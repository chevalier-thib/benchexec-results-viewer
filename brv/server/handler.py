#!/usr/bin/python

import sys
if (sys.version_info > (3, 0)):
    from http.server import SimpleHTTPRequestHandler
else:
    from SimpleHTTPServer import SimpleHTTPRequestHandler

from brv.datamanager import DataManager
from .. utils import dbg

try:
    from quik import FileLoader
except ImportError:
    print('Sorry, need quik framework to work.')
    print('Run "pip install quik" or check "http://quik.readthedocs.io/en/latest/"')
    sys.exit(1)

# the tools manager object -- it must be globals,
# since handler is created for each request and we do
# not want to create it again and again
datamanager = DataManager('database.conf')

def _render_template(wfile, name, variables):
    loader = FileLoader('html/templates/')
    template = loader.load_template(name)
    wfile.write(template.render(variables,
                                loader=loader).encode('utf-8'))

def showRoot(wfile, args):
    datamanager.refresh()
    _render_template(wfile, 'index.html', {'tools' : datamanager.getTools(),
                                           'otherTools' : datamanager.getOtherToolsByName(),
                                           'uniqueTools' : datamanager.getUniqueToolsByName(),
                                           'otherKeys' : datamanager.getOtherKeysByName()})

def _parse_args(args):
    opts = {}
    for a in args:
        tmp = a.split('=', 1)
        if len(tmp) != 2:
            print('ERROR: unhandled GET arg: {0}'.format(a))
            continue
        if tmp[0] in opts:
                opts[tmp[0]].append(tmp[1])
        else:
                opts[tmp[0]] = [tmp[1]]

    return opts

def _get(p, idx):
    return p[idx]

def showResults(wfile, args):
    opts = _parse_args(args)
    datamanager.refresh()
    if not 'run' in opts:
        wfile.write('<h2>No runs of tools given</h2>')
        return

    class BSet(object):
        def __init__(self, name, bid):
            self.name = name
            self.id = bid

        def __hash__(self):
            return self.id

        def __eq__(self, oth):
            return self.id == oth.id

    # list of ToolRunInfo objects
    run_ids = list(map(int, opts['run']))
    runs = datamanager.getToolRuns(run_ids)
    categories = set()
    # there's few of classifications usually, it will be faster in list
    classifications = []
    for run in runs:
        run._stats = datamanager.getToolInfoStats(run.getID())
        for stats in run._stats.getAllStats().values():
            # a pair (name, id)
            categories.add(BSet(stats.getBenchmarksName(), stats.getBenchmarksID()))
            for c in stats.getClassifications():
                if c not in classifications:
                    classifications.append(c)

    # give it some fixed order
    cats = [x for x in categories]

    def _toolsGETList():
        s = ''
        for x in opts['run']:
            s += '&run={0}'.format(x)
        return s

    def _formatClassification(classification):
        color = None
        if classification == 'correct-unconfirmed':
            color = 'orange'
        elif classification.startswith('correct'):
            color = 'green'
        elif classification.startswith('incorrect'):
            color = 'red'
        elif classification.startswith('error'):
            color = 'purple'
        elif classification.startswith('unknown'):
            color = 'gray'

        if color is None:
            return classification
        else:
            return '<span style="color: {0}">{1}</span>'.format(color, classification)

    def _getStats(run, bset_id):
        assert not run is None
        assert not bset_id is None

        return run.getStats().getStatsByID(bset_id)

    def _getCount(stats, classif):
        if stats is None:
            return 0
        else:
            return stats.getCount(classif)

    _render_template(wfile, 'results.html',
                     {'runs':runs, 'benchmarks_sets' : cats,
                      'toolsGETList' : _toolsGETList,
                      'getStats' : _getStats,
                      'getCount' : _getCount,
                      'get' : _get,
                      'classifications' : classifications,
                      'formatClassification' : _formatClassification })


def showBenchmarksResults(wfile, args):
    opts = _parse_args(args)
    if not 'run' in opts:
        wfile.write('<h2>No runs of tools given</h2>')
        return

    if not 'benchmarks' in opts:
        wfile.write('<h2>No benchmarks to show given</h2>')
        return

    run_ids = list(map(int, opts['run']))
    runs = datamanager.getToolRuns(run_ids)

    try:
        bset_id = int(opts['benchmarks'][0])
    except ValueError or KeyError:
        wfile.write('<h2>Invalid benchmarks</h2>')
        return
        
    results = list(datamanager.getRunInfos(bset_id, run_ids).getRows().items())
    print(len(results))
    _render_template(wfile, 'benchmarks_results.html',
                     {'runs' : runs,
                      'get' : _get,
                      'results': results})

def showTools(wfile, args):
    opts = _parse_args(args)
    if 'delete' in opts:
        from .. database.writer import DatabaseWriter
        writer = DatabaseWriter('database.conf')
        writer.deleteTool(int(opts['delete'][0]))
        writer.commit()

        datamanager.refresh()
        _render_template(wfile, 'tools.html', {'tools' : datamanager.getToolsByName(),
                                           'toolKeys' : datamanager.getToolKeys() })
        return

    if 'desc' in opts:
        from .. database.writer import DatabaseWriter
        writer = DatabaseWriter('database.conf')
        ftag = 0
        if 'tags' in opts:
            for tag in opts['tags']:
                if tag == "bold":
                    ftag += 1
                if tag == "italics":
                    ftag += 2
                if tag == "red":
                    ftag += 4
        writer.setDesc(opts['run'][0], opts['desc'][0].replace('+', ' '))
        writer.setTags(opts['run'][0], ftag)
    
    datamanager.refresh()

    _render_template(wfile, 'tools.html', {'tools' : datamanager.getToolsByName(),
                                           'toolKeys' : datamanager.getToolKeys() })
    

def sendStyle(wfile):
    f = open('html/style.css', 'rb')
    wfile.write(f.read())
    f.close()

handlers = {
    'root'              : showRoot,
    'results'           : showResults,
    'benchmarks_results': showBenchmarksResults,
    'tools'             : showTools,
    'style.css'         : None, # we handle this specially
}

# see http://www.acmesystems.it/python_httpd
class Handler(SimpleHTTPRequestHandler):
    def _parsePath(self):
        args = []

        tmp = self.path.split('?')
        path = None
        if len(tmp) == 2:
            path = tmp[0].strip()
            args = tmp[1].split('&')
        elif len(tmp) == 1:
            path = tmp[0]

        if not path:
            return (None, [])

        if path == '' or path == '/':
            return ('root', args)
        else:
            path = path[1:]

        global handlers
        if path in handlers.keys():
            return (path, args)
        else:
            return (None, [])

    def _send_headers(self, mimetype = 'text/html'):
        self.send_response(200)
        self.send_header('Content-type', mimetype)
        self.end_headers()

    def do_GET(self):
        act, args = self._parsePath()

        if act is None:
            self._send_headers()
            self.send_error(404, 'Unhandled request')
            print(self.path)
            return
        elif act == 'style.css':
            self._send_headers('text/css')
            sendStyle(self.wfile)
            return

        global handlers
        assert act in handlers.keys()

        self._send_headers()
        handlers[act](self.wfile, args)

