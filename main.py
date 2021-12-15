import logging
import random

from bottle import record, run, ctx

logger = logging.getLogger("bottleDNS")


# logger.setLevel(0)
# Two examples of simple, static records.
@record('www.localhost.local')
def do_localhost():
    return '127.0.0.1'


@record('zero.com')
def do_zeros():
    return '0.0.0.0'


@record('random.com')
def do_random():
    # Generate a random response each time, because why not.
    octets = [str(random.randint(0, 255)) for x in range(4)]
    return '.'.join(octets)


@record('echo.com')
def do_echo():
    # This just sends the client their own IP address back
    # ctx is of the form: ((client ip, port),DNSRecord(query))
    return ctx[0][0]


@record('*.phonehome.com')
def do_phonehome():
    # Log requests to any subdomain under a given name, useful for finding otherwise blind CSRF/SSRF/etc
    r = ctx[1]
    logger.critical("{} sent a phone home request for: {}".format(ctx[0][0], r.questions[0].qname))
    return '0.0.0.0'


def main():
    run("127.0.0.1", 5553)


if __name__ == '__main__':
    main()
