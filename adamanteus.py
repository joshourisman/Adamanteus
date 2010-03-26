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

    def __init__(self, backend, options):
        self.backend = backend
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
        dump_options = ['mongodump', '--out=%s' % self.path, self.database]

        call(dump_options)
            
def main():
    usage = "usage: %prog -b BACKEND -d DATABASE [-r repository]"
    p = optparse.OptionParser(description=' Backup a database to a mercurial repository',
                              prog='adamanteus',
                              version='adamanteus 0.1a',
                              usage=usage)
    # p.add_option('--backend', '-b', default="mongodb",
    #              help="The type of database to be backed up. (Defaults to mongodb.)")
    p.add_option('--database', '-d', default=None,
                 help="The name of the database to be backed up.")
    p.add_option('--repository', '-r', default=None,
                 help="The mercurial repository to be backed up to.")
    options, arguments = p.parse_args()

    DUMPERS = {
        'mongodb': MongoDumper,
        }

    if len(arguments) != 1:
        p.print_usage()
        print >> sys.stderr, 'You must specify a database backend.'
        return
    else:
        backend = arguments[0]
    if backend not in DUMPERS.keys():
        print >> sys.stderr, '%s is not currently a supported database backend.' % backend
        print >> sys.stderr, 'Supported backends include: %s.' % ', '.join(DUMPERS.keys())
        return
    if options.database is None:
        print p.print_usage()
        print >> sys.stderr, 'You must specify a database to be backed up.'
        return

    dumper = DUMPERS[backend](backend, options)
    dumper()
    
if __name__ == '__main__':
    main()

