#!/usr/bin/env python
import optparse

def main():
    p = optparse.OptionParser()
    p.add_option('--backend', '-b', default="mongodb")
    options, arguments = p.parse_args()
    print 'Preparing to back up a %s database' % options.backend

if __name__ == '__main__':
    main()

