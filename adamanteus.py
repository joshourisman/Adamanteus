#!/usr/bin/env python
import optparse
import sys
from subprocess import call
from mercurial import hg, ui
from mercurial.error import RepoError

DUMPERS = {
    'mongodb': 'mongodump',
    }

def main():
    p = optparse.OptionParser(description=' Backup a database to a mercurial repository',
                              prog='adamanteus',
                              version='adamanteus 0.1a',
                              usage='%prog')
    p.add_option('--backend', '-b', default="mongodb")
    p.add_option('--database', '-d', default=None)
    p.add_option('--repository', '-r', default=None)
    options, arguments = p.parse_args()

    if options.backend != "mongodb":
        print >> sys.stderr, 'Currently, only MongoDB is supported as a database backend.'
        return
    
    if options.repository is not None:
        path = options.repository
    else:
        path = 'adamanteus_%s_backup' % options.backend

    print 'Preparing to back up a %s database to repository %s' % (options.backend, path)

    try:
        r = hg.repository(ui.ui(), path=path)
    except RepoError:
        r = hg.repository(ui.ui(), path=path, create=True)

    dump_options = [DUMPERS[options.backend], '--out=%s' % path]
    if options.database is not None:
        dump_options.append('--db=%s' % options.database)

    call(dump_options)

if __name__ == '__main__':
    main()

