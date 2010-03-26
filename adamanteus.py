#!/usr/bin/env python
import optparse
import sys
from subprocess import call
from mercurial import hg, ui
from mercurial.error import RepoError

DUMPERS = {
    'mongodb': 'mongodump', # For now we need to use mongodump, will switch to mongoexport with MongoDB 1.5
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

    if options.backend not in DUMPERS.keys():
        print >> sys.stderr, '%s is not currently a supported database backend.' % options.backend
        print >> sys.stderr, 'Supported backends include: %s.' % ', '.join(DUMPERS.keys())
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

    status = r.status(unknown=True)
    unknown = status[4]
    missing = status[3]

    if len(unknown):
        print "Adding %d files to repo..." % len(unknown)
        r.add(unknown)
    if len(missing):
        print "Removing %d missing files from repo..." % len(unknown)
        r.remove(missing)
    if len(r.status()[0]) or len(r.status()[1]):
        rev = r.commit()

if __name__ == '__main__':
    main()

