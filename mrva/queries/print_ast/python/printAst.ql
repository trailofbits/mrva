import python
import semmle.python.PrintAst

class SpecificFile extends File {
    SpecificFile() { this.getRelativePath().matches("{MRVA_MATCH}") }
}

class PrintAstConfigurationOverride extends PrintAstConfiguration {
  override predicate shouldPrint(AstNode e, Location l) {
    super.shouldPrint(e, l) and
    l.getFile() instanceof SpecificFile
  }
}
