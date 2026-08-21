import FormalConjectures.ErdosProblems.«1052»

namespace ResultRunnerQualification

theorem source_native : Erdos1052.IsUnitaryPerfect 6 :=
  Erdos1052.isUnitaryPerfect_6

end ResultRunnerQualification

example : Erdos1052.IsUnitaryPerfect 6
 := by exact ResultRunnerQualification.source_native
#print axioms ResultRunnerQualification.source_native
