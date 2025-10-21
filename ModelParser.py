from FMT import (
	Core,					  	# type: ignore					
    Models, 				  	# type: ignore
    Parser, 				  	# type: ignore
    Exception as FMTexception,  # type: ignore
	Parallel 					# type: ignore
)
from pathlib import Path
import shutil

class ModelParser:
	def __init__(self, path: Path, scenarios: list[str], length: int):
		self.path = path
		self.scenarios = scenarios
		self.length = length
		self.modelparser = Parser.FMTmodelparser()
		self._set_to_warnings()
		self.models = self.modelparser.readproject(self.path.as_posix(), self.scenarios)
		self.lpmodel = self._doplanning(length)
		self.threads: int = 1

	def get_outputs_results(self, time: int, outputs: list[str]):
		if time < 0 or time > self.length:
			raise ValueError(f"Time must be between 0 and {self.length}")
		results = {}
		output_objects = self._get_outputs_objects(outputs)
		for output in output_objects:
			results[output.getname()] = self.lpmodel.getoutput(output, time, Core.FMToutputlevel.standard)

		return results
	
	def _get_outputs_objects(self, outputs: list[str]):
		output_objects = []
		for output in self.lpmodel.getoutputs():
			if output.getname() in outputs:	
				output_objects.append(output)

		return output_objects

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
	
	def create_replanning_models(self) -> tuple[Models.FMTlpmodel, Models.FMTnssmodel, Models.FMTlpmodel]:
		if len(self.models) < 3:
			raise Exception("3 Models are required for replanning")
		
		strategic = Models.FMTlpmodel(self.models[0], Models.FMTsolverinterface.MOSEK)
		stochastic = Models.FMTnssmodel(self.models[1], 0)
		tactic = Models.FMTlpmodel(self.models[2], Models.FMTsolverinterface.MOSEK)

		return strategic, stochastic, tactic

	def _set_replanning(self, 
			strategic: Models.FMTlpmodel,
			stochastic: Models.FMTnssmodel,
			tactic: Models.FMTlpmodel,
			selected_outputs: list[str], 
			output_location: str, 
			length: int,
			replicates: int,
			drift: float = 0.5,
			output_level: Core.FMToutputlevel = Core.FMToutputlevel.standard,
			write_schedule = True) -> Parallel.FMTreplanningtask:

		self.replanning_task = Parallel.FMTreplanningtask(
			strategic,
			stochastic, 
			tactic,
			self._get_outputs_objects(selected_outputs),
			output_location, 
			"CSV", 
			["SEPARATOR=SEMICOLON"],
			replicates,
			length,
			drift, 
			output_level,
			write_schedule)
		
		return self.replanning_task

	def replanning(self,
			strategic: Models.FMTlpmodel,
			stochastic: Models.FMTnssmodel,
			tactic: Models.FMTlpmodel,
			selected_outputs: list[str], 
			output_location: str, 
			length: int,
			replicates: int,
			threads: int = 1,
			drift: float = 0.5,
			output_level: Core.FMToutputlevel = Core.FMToutputlevel.standard,
			write_schedule = True,
			ondemandrun: bool = True):
		
		self._clear_folder(output_location)
		
		if length < 1:
			raise ValueError("Time must be greater than 1")
		
		strategic.setparameter(Models.FMTintmodelparameters.LENGTH, length)
		strategic.setparameter(Models.FMTintmodelparameters.NUMBER_OF_THREADS, threads)
		stochastic.setparameter(Models.FMTintmodelparameters.LENGTH, 1)
		tactic.setparameter(Models.FMTintmodelparameters.LENGTH, 1)
		tactic.setparameter(Models.FMTintmodelparameters.NUMBER_OF_THREADS, threads)
		
		replanning_task = self._set_replanning(
			strategic,
			stochastic,
			tactic,
			selected_outputs,
			output_location,
			length,
			replicates,
			drift,
			output_level,
			write_schedule)
		
		self.modelparser.setdebuglogger()
		self.modelparser.setdebugexceptionhandler()
		
		handler = Parallel.FMTtaskhandler(
			replanning_task, 
			self.threads)

		try:
			if ondemandrun:
				handler.ondemandrun()
			else:
				handler.conccurentrun()
		except FMTexception.FMTexception as e:
			print("An error occurred during replanning:", e)

	def _clear_folder(self, folder_path: str | Path):
		folder = Path(folder_path)

		if not folder.exists():
			raise FileNotFoundError(f"Le dossier spécifié n'existe pas : {folder}")
		if not folder.is_dir():
			raise NotADirectoryError(f"Le chemin spécifié n'est pas un dossier : {folder}")

		for item in folder.iterdir():
			try:
				if item.is_file() or item.is_symlink():
					item.unlink() 
				elif item.is_dir():
					shutil.rmtree(item) 
			except Exception as e:
				raise e

	def _find_value(self, output_results: dict):
		if len(self.models) < 3:
			raise Exception("Models for strategic, stochastic and tactic are required")
		
		final_value = {}
		for output, results in output_results.items():
			for key, value in results.items():
				if value == 0:
					continue
				
				strategic, stochastic, tactic = self.create_replanning_models()

				for model in [strategic, stochastic, tactic]:
					area_to_keep = []
					for area in model.getarea():
						if key in str(area):
							area_to_keep.append(area)
					model.setarea(area_to_keep)
				
				is_valid = False
				factors_tested = [0.5]
		
				new_constraint = Core.FMTconstraint(
					Core.FMTconstrainttype.FMTstandard, 
					self._get_outputs_objects([output])[0])
				new_constraint.setlength(1, self.length)
				new_constraint.setrhs(value * factors_tested[-1], value * factors_tested[-1])

				#constraints = strategic.getconstraints() 
				#constraints.append(new_constraint)
				#strategic.setconstraints(constraints)

				self.replanning(
					strategic,
					stochastic,
					tactic,
					[output],
					"C:/Users/Admlocal/Documents/SCRAP1",
					length=self.length,
					replicates=1,
					threads=self.threads,)

				print("Yo")
			

	
# surles3modèle.getarea()
# .setarea()

# Le reste juste sur le stratégique
# .setconstraint()
# Poss2 = Core.FMTconstraint(Core.FMTconstrainttype.FMTstandard, outputs[0])
# Poss2.setrhs(100,100)
# Poss2.setlength(1, length)

if __name__ == "__main__":
	path = Path("C:\\Users\\Admlocal\\Documents\\issues\\C2_00985788\\CC_modele_feu\\WS_CC\\Feux_2023_ouest_V01.pri")
	scenarios = ["strategique_CC", "stochastique_CC", "tactique_CC"]
	model = ModelParser(path, scenarios, 5)
	output_results = model.get_outputs_results(1, ["OVOLTOTREC"])
	
	#strategic, stochastic, tactic = model.create_replanning_models()
	#model.replanning(
	#	strategic,
	#	stochastic,
	#	tactic,
	#	["OVOLTOTREC"], 
	#	"C:/Users/Admlocal/Documents/SCRAP", 
	#	length=1,
	#	replicates=1,
	#	threads=1)
	
	model._find_value(output_results)
