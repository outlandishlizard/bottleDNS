# bottleDNS

A tiny python DNS server providing a "flask-like" decorator-based interface. Provided under the MIT license, see LICENSE

The main use case I had in mind building this was security research-- I needed a DNS server whose behavior (including
logging) was easy to tweak quickly.

Currently the feature set is pretty minimal-- only A records have been tested, and there's no support for importing zone
files or anything fancy like that.

# Usage

main.py contains several examples of how to use this library.