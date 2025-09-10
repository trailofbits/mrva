import ruby
import codeql.ruby.AST
import codeql.ruby.printAst

class SpecificFile extends File {
    SpecificFile() { this.getRelativePath().matches("{MRVA_MATCH}") }
}

class PrintAstConfigurationOverride extends PrintAstConfiguration {
  override predicate shouldPrintAstEdge(AstNode parent, string edgeName, AstNode child) {
    super.shouldPrintAstEdge(parent, edgeName, child) and
    parent.getFile() instanceof SpecificFile
  }

  override predicate shouldPrintNode(AstNode n) {
    super.shouldPrintNode(n) and
    n.getFile() instanceof SpecificFile
  }
}
