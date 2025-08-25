/**
 * @name Test path-problem query
 * @id path-problem
 * @description Test path-problem query
 * @kind path-problem
 * @tags security
 * @problem.severity error
 * @precision high
 */

// https://codeql.github.com/docs/codeql-language-guides/analyzing-data-flow-in-python/

import python
import semmle.python.dataflow.new.TaintTracking
import semmle.python.ApiGraphs

module EnvironmentToFileConfiguration implements DataFlow::ConfigSig {
  predicate isSource(DataFlow::Node source) {
    source = API::moduleImport("os").getMember("getenv").getACall()
  }

  predicate isSink(DataFlow::Node sink) {
    exists(DataFlow::CallCfgNode call |
      call = API::moduleImport("os").getMember("open").getACall() and
      sink = call.getArg(0)
    )
  }
}

module EnvironmentToFileFlow = TaintTracking::Global<EnvironmentToFileConfiguration>;
import EnvironmentToFileFlow::PathGraph

from EnvironmentToFileFlow::PathNode env, EnvironmentToFileFlow::PathNode open
where EnvironmentToFileFlow::flowPath(env, open)
select open.getNode(), env, open, "Found os.getenv to os.open"
