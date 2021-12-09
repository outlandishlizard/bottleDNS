from collections import defaultdict
from socketserver import ThreadingUDPServer, BaseRequestHandler

import dnslib

records = defaultdict(dict)
_ctx = None


# We need this "proxy" object because directly importing _ctx doesn't preserve mutations made to it in this scope--
# it remains None forever if imported directly. This is way less neat than werkzeug's approach which works with
# greenlets etc-- this implementation is only going to work right for threads.
class BottleContext(object):
    def __getitem__(self, key):
        return _ctx.__getitem__(key)

    def __getattr__(self, key):
        return _ctx.__getattr__(key)


ctx = BottleContext()


class NameTree(object):
    # This class implements a hostname "tree" using nested dictionaries, with support for using * as a wildcard at any
    # layer of the name. The special key NameTree.LEAVES is used to store the functions that generate records for the 
    # name at the given layer.
    # So an A record for www.example.com of 1.2.3.4 becomes:
    # {"com":
    #   {example:
    #       {www:
    #       {LEAVES:{'A': lambda: '1.2.3.4'}
    #       }
    #   }
    # }
    # lambda notation is used here rather than defining a very simple function that takes no arguments and returns
    # '1.2.3.4' for the sake of brevity, you'd normally bind to a named function here using the @record decorator.
    LEAVES = 0

    def __init__(self):
        self.tree = {}

    def get(self, name):
        # We want to use DNSLabel here so we can piggyback on the parsing and equality logic in dnslib, rather than
        # having to write our own. Theoretically, this will also make adding pattern-matching support to the @record
        # decorator easier later, as DNSLabel already supports it.
        if isinstance(name, str):
            name = dnslib.DNSLabel(name)
        names = name.label
        subtree = self.tree
        for count, level in enumerate(names[::-1]):
            if level in subtree:
                subtree = subtree[level]
            elif b'*' in subtree:
                subtree = subtree[b'*']
            else:
                raise KeyError("{} not present in dictionary".format(name))

            if count == len(names) - 1:
                if NameTree.LEAVES in subtree:
                    return subtree[NameTree.LEAVES]
                else:
                    raise KeyError("{} not present in dictionary".format(name))

    def insert(self, name, value, rtype='A'):
        # We want to use DNSLabel here so we can piggyback on the parsing and equality logic in dnslib, rather than
        # having to write our own. Theoretically, this will also make adding pattern-matching support to the @record
        # decorator easier later, as DNSLabel already supports it.
        if isinstance(name, str):
            name = dnslib.DNSLabel(name)
        names = name.label
        subtree = self.tree
        for count, level in enumerate(names[::-1]):
            if level not in subtree:
                subtree[level] = {}
            subtree = subtree[level]
            if count == len(names) - 1:
                if NameTree.LEAVES not in subtree:
                    subtree[NameTree.LEAVES] = defaultdict(list)
                subtree[NameTree.LEAVES][rtype].append(value)


lookup = NameTree()


def register_record(qname, fn, rtype='A'):
    lookup.insert(qname, fn, rtype=rtype)


def record(qname, rtype='A'):
    def wrapper(fn):
        register_record(qname, fn)
        return fn

    return wrapper


class BottleHandler(BaseRequestHandler):
    def handle(self):
        # This is kind of a hack, but sets up ctx as a thread local, flask-style (I hope?).
        global _ctx

        data = self.request[0]
        req = dnslib.DNSRecord.parse(data)
        _ctx = (self.client_address, req)
        resp = printreq(req)
        sock = self.request[1]
        sock.sendto(resp, self.client_address)


def printreq(req):
    # TODO this is a mess
    qname = req.questions[0].qname
    addr_fn = lookup.get(qname)['A'][0]
    addr = addr_fn()
    rd = dnslib.A(addr)
    rr = dnslib.RR(qname, rdata=rd)
    response = dnslib.DNSRecord(dnslib.DNSHeader(id=req.header.id, rname=req.q.qname))
    response.add_answer(rr)
    return response.pack()


def run(addr, port):
    # No TCP support for the moment :(.
    server = ThreadingUDPServer((addr, port), BottleHandler)
    print("Listening on {}:{}".format(addr, port))
    server.serve_forever()
