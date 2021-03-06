#!/usr/bin/python

from brv.toolsmanager import ToolsManager
from brv.toolruninfo import RunInfosTable

class DataManager(object):
    """
    Instance of this class manages all data (either from xml
    or database) that we know about, so this is the top
    class wrapping all retrieved data
    """

    def __init__(self, db_conf = None, xmls = []):
        self.toolsmanager = ToolsManager()
        self._db = None

        if db_conf:
            from brv.database.reader import DatabaseReader
            self._db = DatabaseReader(db_conf)

            tool_runs = self._db.getToolRuns()
            for run in tool_runs:
                self.toolsmanager.add(run)

        if xmls:
            # XXX: NOT SUPPORTED YET. load the xml into database first
            pass

    def refresh(self):
        if self._db:

            self.toolsmanager = ToolsManager()
            tool_runs = self._db.getToolRuns()
            for run in tool_runs:
                self.toolsmanager.add(run)


    def getTools(self):
        return self.toolsmanager.getTools()

    def getToolsByName(self):
        res = {}
        alltools = self.getTools()
        for tool in alltools:
            if tool.name in res:
                res[tool.name].append(tool)
            else:
                res[tool.name] = [tool]
        return res

    def getToolKeys(self):
        return list(self.getToolsByName().keys())

    def getOtherKeysByName(self):
        return list(self.getOtherToolsByName().keys())

    def getUniqueToolsByName(self):
        res = []
        alltools = self.getToolsByName()
        for name in alltools.keys():
            if len(alltools[name]) == 1:
                res.append(alltools[name][0])
        return res

    def getOtherToolsByName(self):
        res = {}
        alltools = self.getToolsByName()
        for name in alltools.keys():
            if len(alltools[name]) != 1:
                res[name] = alltools[name]
        return res
    
    def getUniqueTools(self):
        alltools = self.getTools()
        return [tool for tool in alltools if tool.nbRuns() == 1]

    def getToolRuns(self, which = []):
        return self.toolsmanager.getToolRuns(which)

    def getToolInfoStats(self, which):
        return self._db.getToolInfoStats(which)

    def getRunInfos(self, bset_id, toolruns_id):
        table = RunInfosTable()
        for tid in toolruns_id:
            table.add(self._db.getRunInfos(bset_id, tid))

        return table


