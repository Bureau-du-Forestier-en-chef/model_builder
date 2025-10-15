from FMT import (
	Core,					  	# type: ignore					
    Models, 				  	# type: ignore
    Parser, 				  	# type: ignore
    Exception as FMTexception 	# type: ignore
)
from pathlib import Path

class ModelParser:
	def __init__(self, path: Path, scenario: list[str], length: int):
		self.path = path
		self.scenario = scenario
		self.modelparser = Parser.FMTmodelparser()
		self._set_to_warnings()
		self.models = self.modelparser.readproject(self.path.as_posix(), self.scenario)
		self.lpmodel = self._doplanning(length)

	def get_outputs(self, time: int, outputs: list[str]):
		results = {}
		for output in self.lpmodel.getoutputs():
			if output.getname() in outputs:	
				results[output.getname()] = self.lpmodel.getoutput(output, time, Core.FMToutputlevel.standard)

		return results

	def _set_to_warnings(self):
		self.modelparser.seterrorstowarnings([
			FMTexception.FMTexc.FMToveridedyield,
			FMTexception.FMTexc.FMTmissingyield,
			FMTexception.FMTexc.FMTdeathwithlock,
			FMTexception.FMTexc.FMToutput_too_much_operator,
			FMTexception.FMTexc.FMToutput_missing_operator,
			FMTexception.FMTexc.FMTinvalidyield_number,
			FMTexception.FMTexc.FMTundefinedoutput_attribute])
	
	def _doplanning(self, length: int):
		if length < 1:
			raise ValueError("Time must be greater than 1")
		
		lpmodel = Models.FMTlpmodel(self.models[0], Models.FMTsolverinterface.MOSEK) # CLP ou MOSEK
		lpmodel.setparameter(Models.FMTintmodelparameters.LENGTH, length)
		lpmodel.setparameter(Models.FMTboolmodelparameters.FORCE_PARTIAL_BUILD, True)
		lpmodel.doplanning(True)
		
		return lpmodel

	def _get_file_path(self, ext: str):
		for file in self.path.parent.iterdir():
			if file.suffix == ext:
				return file


if __name__ == "__main__":
	path = Path("T:/Donnees/02_Courant/07_Outil_moyen_methode/01_Entretien_developpement/Interne/FMT/Entretien/Modeles_test/02661/PC_9307_U02661_4_Vg2_2023_vRP1f.pri")
	scenarios = ["14_Sc5_Determin_apsp"]
	model = ModelParser(path, scenarios, 1)
	model.get_outputs(1, ["OVOLTOTREC"])
