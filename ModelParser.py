from FMT import (
	Core,					  	# type: ignore					
    Models, 				  	# type: ignore
    Parser, 				  	# type: ignore
    Exception as FMTexception,  # type: ignore
	Parallel 					# type: ignore
)
from pathlib import Path
import shutil
from Logger import Logging

class ModelParser:
	def __init__(self, path: Path, scenarios: list[str], length: int):
		self.Logging = Logging(path.stem + ".log")
		self.path = path
		self.scenarios = scenarios
		self.length = length
		self.modelparser = Parser.FMTmodelparser()
		self.modelparser.setdebuglogger()
		self.modelparser.setdebugexceptionhandler()
		self._set_to_warnings()
		self.models = self.modelparser.readproject(self.path.as_posix(), self.scenarios)
		self.lpmodel = self._doplanning(length)
		self.threads: int = 1

	def get_outputs_results(self, time: int, outputs: list[str]):
		if time < 0 or time > self.length:
			self.Logging.log_message("ERROR", f"Time {time} is out of bounds (0-{self.length})")
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
			self.Logging.log_message("ERROR", "Length must be greater than 1")
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
			self.Logging.log_message("ERROR", "3 Models are required for replanning")
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

		replanning_task = Parallel.FMTreplanningtask(
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
		
		return replanning_task

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
			self.Logging.log_message("ERROR", "Length must be greater than 1")
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
		
		handler = Parallel.FMTtaskhandler(
			replanning_task, 
			self.threads)

		try:
			if ondemandrun:
				handler.ondemandrun()
			else:
				handler.conccurentrun()
		except FMTexception.FMTexception as e:
			self.Logging.log_message("ERROR", f"Replanning failed: {str(e)}")
			raise RuntimeError(f"Replanning failed: {str(e)}")

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
	
	def _inspect_csv(self, output_name: str, id_type: str, value: float, field_path: str | Path) -> bool:
		field_file = Path(field_path) / f"{self.scenarios[2]}.csv"
		is_valid = True

		for line in field_file.read_text().splitlines():
			line_splited = line.strip().split(";")
			if line_splited[2] == output_name and line_splited[3].strip('"') == id_type:
				if float(line_splited[-1]) < value:
					is_valid = False
					break 
		return is_valid
	
	def _find_factor(self, 
			strategic: Models.FMTlpmodel,
			stochastic: Models.FMTnssmodel,
			tactic: Models.FMTlpmodel,
			output: str,
			key: str,
			value: float,
			workspace: str,
			threads: int = 1):
		
		factor_min = 0
		factor_max = 100
		iterations = 0

		while (factor_max - factor_min) > 1 and iterations <= 8:

			factor_tested = ((factor_min + factor_max) // 2) / 100
			
			new_constraint = Core.FMTconstraint(
				Core.FMTconstrainttype.FMTstandard, 
				self._get_outputs_objects([output])[0])
			new_constraint.setlength(1, self.length)
			new_constraint.setrhs(value * factor_tested, value * factor_tested)
			constraints = strategic.getconstraints() 
			constraints.append(new_constraint)
			strategic.setconstraints(constraints)

			try:
				self.replanning(
					strategic,
					stochastic,
					tactic,
					[output],
					workspace,
					length=self.length,
					replicates=1,
					threads=threads)
				
			except RuntimeError as e:
				if "FMTexc(53)Function failed: Infeasible Global model"	in str(e):
					factor_max = factor_tested * 100
					self.Logging.log_message("INFO", 
							(f"Iteration {iterations}: Infeasible model for factor {factor_tested:.2f}. "
							f"Reducing max factor to {factor_max / 100:.2f}.")
						)
				else:
					raise e

			else:
				if not self._inspect_csv(
						output, 
						key, 
						value * factor_tested, 
						workspace):
					factor_max = factor_tested * 100
					self.Logging.log_message("INFO", 
							(f"Iteration {iterations}: Output value not met for factor "
							f"{factor_tested:.2f}. Reducing max factor to {factor_max / 100:.2f}.")
						)
				else:
					factor_min = factor_tested * 100
					self.Logging.log_message("INFO", 
							(f"Iteration {iterations}: Output value met for factor " 
							f"{factor_tested:.2f}. Increasing min factor to {factor_min / 100:.2f}.")
						)

			finally:
				constraints.remove(new_constraint)
				strategic.setconstraints(constraints)
				iterations += 1
				self.Logging.log_message("INFO", 
						(f"End of iteration {iterations} with factor range: "
						f"{factor_min / 100:.2f} - {factor_max / 100:.2f}.")
					)
		
		return factor_min / 100

	def _change_area(self, model, key: str):
		area_to_keep = []
		for area in model.getarea():
			if key in str(area):
				area_to_keep.append(area)
		model.setarea(area_to_keep)

	def find_max_value(self, output_results: dict, workspace: str = "C:/Users/Admlocal/Documents/SCRAP1", threads: int = 1):
		if len(self.models) < 3:
			raise Exception("Models for strategic, stochastic and tactic are required")
		
		final_values = {}
		for output, results in output_results.items():
			for key, value in results.items():
				if value == 0:
					continue
			
				strategic, stochastic, tactic = self.create_replanning_models()

				for model in [strategic, stochastic, tactic]:
					self._change_area(model, key)

				best_factor = self._find_factor(
					strategic,
					stochastic,
					tactic,
					output,
					key,
					value,
					workspace,
					threads)
				
				self.Logging.log_message("INFO", 
						f"Best factor found for output {output} and key {key} is {best_factor:.4f}.")

				if output not in final_values:
					final_values[output] = {key: best_factor}
				else:
					final_values[output][key] = best_factor
	
		return final_values		


if __name__ == "__main__":
	path = Path("C:\\Users\\Admlocal\\Documents\\issues\\C2_00985788\\CC_modele_feu\\WS_CC\\Feux_2023_ouest_V01.pri")
	scenarios = ["strategique_CC", "stochastique_vide", "tactique_CC"]
	model = ModelParser(path, scenarios, 5)
	output_results = model.get_outputs_results(1, ["OVOLTOTREC"])
	
	results = model.find_max_value(output_results, threads=5)
	print(results)
