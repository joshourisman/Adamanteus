#!/usr/bin/env python
import optparse
import sys
from subprocess import call
from mercurial import hg, ui
from mercurial.error import RepoError

class Dumper(object):
    """
    Main class that defines how to store database dumps in version control.
    Will be subclassed for the different database backends to handle the
    different methods of doing the actual dump.
    """

    def __init__(self, options):
        self.backend = options.backend
        self.database = options.database
        
        if options.repository is not None:
            self.path = options.repository
        else:
            self.path = 'adamanteus_%s_backup' % self.backend
        print 'Preparing to back up a %s database to repository %s' % (self.backend, self.path)

        try:
            self.repo = hg.repository(ui.ui(), path=self.path)
        except RepoError:
            self.repo = hg.repository(ui.ui(), path=self.path, create=True)

    def __call__(self):
        self.dump()
        self.store()

    def dump(self):
        raise NotImplementedError("You must subclass Dumper and define "
                                  "your own dump() method.")

    def store(self):
        status = self.repo.status(unknown=True)
        unknown = status[4]
        missing = status[3]

        if len(unknown):
            print "Adding %d files to repo..." % len(unknown)
            self.repo.add(unknown)
        if len(missing):
            print "Removing %d missing files from repo..." % len(unknown)
            self.repo.remove(missing)
        if len(self.repo.status()[0]) or len(self.repo.status()[1]):
            rev = self.repo.commit()

class MongoDumper(Dumper):
    """
    Subclass of Dumper for working with MongoDB databases.
    """

    def dump(self):
        # For now we need to use mongodump, will switch to
        # mongoexport with MongoDB 1.5
        dump_options = ['mongodump', '--out=%s' % self.path]
        if self.database is not None:
            dump_options.append('--db=%s' % self.database)

        call(dump_options)

DUMPERS = {
    'mongodb': MongoDumper,
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
    else:
        dumper = DUMPERS[options.backend](options)
        dumper()
    
if __name__ == '__main__':
    main()

