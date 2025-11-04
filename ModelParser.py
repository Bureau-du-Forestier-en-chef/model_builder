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
	def __init__(self, path: Path, scenarios: list[str], length: int, logger_suffix: str | None = None):
		self.Logging = Logging(f"{path.stem}{logger_suffix or ''}.log")
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

	def get_outputs_results(self, time: int, outputs: list[str] | list[Core.FMToutput]) -> dict:
		if time < 0 or time > self.length:
			self.Logging.log_message("ERROR", f"Time {time} is out of bounds (0-{self.length})")
			raise ValueError(f"Time must be between 0 and {self.length}")
		results = {}

		if not isinstance(outputs[0], Core.FMToutput):
			output_objects = self._get_outputs_objects(outputs)
		else:
			output_objects = outputs
		for output in output_objects:
			results[output.getname()] = self.lpmodel.getoutput(output, time, Core.FMToutputlevel.standard) # type: ignore

		return results
	
	def _get_outputs_objects(self, outputs: list[str]):
		output_objects = []
		for output in self.lpmodel.getoutputs():
			if output.getname() in outputs:	
				output_objects.append(output)
		
		if len(output_objects) < 1:
			msg = f"No output object found for these value {outputs}"
			raise Exception(msg)
		elif len(output_objects) != len(outputs):
			Logging.log_message("WARNING", 
				f"Outputs object not found for: {set(outputs) - set([i.getname() for i in output_objects])}")

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
	
	def _doplanning(self, length: int) -> Models.FMTlpmodel:
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
	
	def _create_workspace_folder(self, base_path: str | Path):
		base_folder = Path(base_path)
		if not base_folder.exists():
			base_folder.mkdir(parents=True, exist_ok=True)

	def replanning(self,
			strategic: Models.FMTlpmodel,
			stochastic: Models.FMTnssmodel,
			tactic: Models.FMTlpmodel,
			selected_outputs: list[str], 
			output_location: Path, 
			length: int,
			replicates: int,
			threads: int = 1,
			drift: float = 0.5,
			output_level: Core.FMToutputlevel = Core.FMToutputlevel.standard,
			write_schedule = True,
			ondemandrun: bool = True):
		
		output_location = output_location / "output"

		if output_location.exists():
			self._clear_folder(output_location)
		self._create_workspace_folder(output_location)

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
			output_location.as_posix(),
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
	
	def _inspect_csv(self, output_name: str, id_type: str, value: float, field_path: str | Path) -> tuple[bool, str]:
		field_file = Path(field_path) / f"{self.scenarios[2]}.csv"
		is_valid = True
		TOLERANCE = 1
		msg = "Output value meets the required threshold at this time."
		max_period = 0
		
		if not field_file.exists():
			raise FileNotFoundError(f"Field file not found: {field_file}")

		for line in field_file.read_text().splitlines():
			line_splited = line.strip().split(";")
			if line_splited[2] == output_name and line_splited[3].strip('"') == id_type:
				max_period = max(max_period, int(line_splited[1]))
				# J'ai ajouté +1 pour éviter les problèmes d'arrondi flottant
				if float(line_splited[-1]) + TOLERANCE < value and is_valid:
					is_valid = False
					msg = (f"Output {output_name} for id {id_type} has value {line_splited[-1]}, "
							f"which is less than the required value {value}. "
							f"At period {line_splited[1]} / ")
		
		if not is_valid:
			msg += f"{max_period}"
				 
		return is_valid, msg
	
	def _find_factor(self, 
			strategic: Models.FMTlpmodel,
			stochastic: Models.FMTnssmodel,
			tactic: Models.FMTlpmodel,
			output: str,
			key: str,
			value: float,
			workspace: Path,
			threads: int = 1,
			known_values: dict | None = None) -> float:
		
		factor_min = 0
		factor_max = 101 # À 101 pour inclure 1.0 dans la recherche = [min, max[
		
		if known_values and output in known_values and key in known_values[output]:
			factor_min = int(known_values[output][key]['min'] * 100)
			factor_max = int(known_values[output][key]['max'] * 100)
			self.Logging.log_message("INFO", 
					(f"Using known factor {known_values[output][key]} for output {output} and key {key}."))

		iterations = 0

		while (factor_max - factor_min) > 1 and iterations <= 8:
			factor_tested = ((factor_min + factor_max) // 2) / 100
			
			workspace_id = workspace / f"{output}_{key}_{factor_tested}"
			self._create_workspace_folder(workspace_id)
			self.modelparser.redirectlogtofile(workspace_id.as_posix() + "/output.log")

			self.Logging.log_message("INFO",
					(f"Iteration {iterations}: Testing factor {factor_tested:.2f} "
					f"for constraint value of {value * factor_tested:.2f}.")
				)

			new_constraint = Core.FMTconstraint(
				Core.FMTconstrainttype.FMTstandard, 
				self._get_outputs_objects([output])[0])
			new_constraint.setlength(1, self.length)
			new_constraint.setrhs(0, value * factor_tested)
			constraints = strategic.getconstraints()      
			constraints.append(new_constraint)
			strategic.setconstraints(constraints)

			try:
				self.replanning(
					strategic,
					stochastic,
					tactic,
					[output],
					workspace_id,
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
				is_valid, msg = self._inspect_csv(output, key, value * factor_tested, workspace_id / "output")
				if not is_valid and msg:
					factor_max = factor_tested * 100
					self.Logging.log_message("INFO", msg)
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


	def find_max_value(self, 
			output_list: list[str],
			workspace: str, 
			threads: int = 1, 
			known_values: dict | None = None) -> dict:
		if len(self.models) < 3:
			raise Exception("Models for strategic, stochastic and tactic are required")
		
		output_results = self.get_outputs_results(1, output_list)

		final_values = {}
		for output, results in output_results.items():
			for key, value in results.items():
				if key in ["NA", "Total"] or value == 0:
					continue

				self.Logging.log_message("INFO", 
						f"Finding max factor for output {output} with target value {value} for key {key}.")

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
					Path(workspace),
					threads, 
					known_values)
				
				self.Logging.log_message("INFO", 
						f"Best factor found for output {output} and key {key} is {best_factor:.2f}.")

				if output not in final_values:
					final_values[output] = {key: best_factor}
				else:
					final_values[output][key] = best_factor
	
		return final_values
	
	
	def _change_area(self, model, key: str):
		area_to_keep = []
		for area in model.getarea():
			if key in str(area):
				area_to_keep.append(area)
		self.Logging.log_message("INFO", 
			f"Keeping {len(area_to_keep)} / {len(model.getarea())} area for key {key}.")
		model.setarea(area_to_keep)

	def _get_constraints_values_in_dict(self,
			dict_values: dict,
			type_id: str):
		to_keep = {}
		for output in dict_values:
			for key in dict_values[output]:
				if key == type_id:
					to_keep[output] = dict_values[output][key]
		
		return to_keep

	def find_combined_max_values(self, 
			output_list: list[str], 
			workspace: str,
			threads: int = 1, 
			known_values: dict | None = None) -> tuple[dict, dict]:
		if len(self.models) < 3:
			raise Exception("Models for strategic, stochastic and tactic are required")
		
		self._clear_folder(workspace)

		output_results = self.get_outputs_results(1, output_list)
		
		final_values = {}
		iteration = 0
		for output in output_list:
			self.Logging.log_message("INFO",  f"Iterating over {output}")
			for key, value in output_results[output].items():
				if key in ["NA", "Total"] or value == 0:
					continue
			
				self.modelparser.redirectlogtofile(workspace + "/output.log")
				strategic, stochastic, tactic = self.create_replanning_models()	

				constraints_added = []
				if iteration > 0:
					# On ajoute les contraintes de l'itération précédente
					existing_constraints = self._get_constraints_values_in_dict(final_values, key)
					for output_constraint, result in existing_constraints.items():
						new_value = result['value'] * result['factor']
						new_constraint = Core.FMTconstraint(
							Core.FMTconstrainttype.FMTstandard, 
							self._get_outputs_objects([output_constraint])[0])
						new_constraint.setlength(1, self.length)
						new_constraint.setrhs(0, new_value)
						constraints_added.append(new_constraint)
						constraints = strategic.getconstraints() 
						constraints.append(new_constraint)
						strategic.setconstraints(constraints)
					self.Logging.log_message("INFO",
						f"Added {len(constraints_added)} constraints for a total of "
						f"{len(constraints)} based on previous iteration results for key {key}.") # type: ignore

					# On réajuste la valeur des outputs
					lpmodel = Models.FMTlpmodel(self.models[0], Models.FMTsolverinterface.MOSEK)
					lpmodel.setparameter(Models.FMTintmodelparameters.LENGTH, self.length)
					lpmodel.setparameter(Models.FMTboolmodelparameters.FORCE_PARTIAL_BUILD, True)
					
					constraints = lpmodel.getconstraints()
					constraints.extend(constraints_added) 
					lpmodel.setconstraints(constraints)

					lpmodel.doplanning(True)
					output_object = self._get_outputs_objects([output])[0]
					new_output_to_acheive = lpmodel.getoutput(output_object, 1, Core.FMToutputlevel.standard)
					self.Logging.log_message("INFO",
						f"Setting new target value for output {output}. Difference of "
						f"{output_results[output][key] - new_output_to_acheive[key]} "	
						f"based on previous iteration results.")		
					output_results[output] = new_output_to_acheive


				self.Logging.log_message("INFO", 
						f"Finding max factor for target value {value} for key {key}.")

				for model in [strategic, stochastic, tactic]:
					self._change_area(model, key)

				best_factor = self._find_factor(
					strategic,
					stochastic,
					tactic,
					output,
					key,
					value,
					Path(workspace),
					threads, 
					known_values)
				
				if iteration > 0:
					for const in constraints_added:
						constraints.remove(const) #type: ignore
					strategic.setconstraints(constraints) #type: ignore 

				self.Logging.log_message("INFO", 
						f"Best factor found for output {output} and key {key} is {best_factor:.2f}.")

				if output not in final_values:
					final_values[output] = {key: {'value': value, 'factor': best_factor}}
				else:
					final_values[output][key] = {'value': value, 'factor': best_factor}
			iteration += 1
	
		return final_values, output_results
	

	def find_max_values_with_obj(self, 
				output_list: list[str], 
				workspace: str,
				threads: int = 1, 
				known_values: dict | None = None) -> dict:
		if len(self.models) < 3:
			raise Exception("Models for strategic, stochastic and tactic are required")
		
		self._clear_folder(workspace)

		output_results = self.get_outputs_results(1, output_list)
		
		final_values = {}

		for output in output_list:
			self.Logging.log_message("INFO",  f"Iterating over {output}")
			self.modelparser.redirectlogtofile(workspace + "/output.log")
			output_object = self._get_outputs_objects([output])[0]
			
			# Nouvelle fonction objective
			new_objective = Core.FMTconstraint(
				Core.FMTconstrainttype.FMTMAXMINobjective, 
				output_object)
			new_objective.setlength(1, self.length)
			new_objective.setpenalties("-", ["_ALL"])

			# On réajuste la valeur des outputs
			lpmodel = Models.FMTlpmodel(self.models[0], Models.FMTsolverinterface.MOSEK)
			lpmodel.setparameter(Models.FMTintmodelparameters.LENGTH, self.length)
			lpmodel.setparameter(Models.FMTboolmodelparameters.FORCE_PARTIAL_BUILD, True)
			lp_constraints = lpmodel.getconstraints()
			Logging.log_message("INFO", 
				f"Nombre de contraites totale: {len(lp_constraints)}")
			lp_constraints[0] = new_objective
			lpmodel.setconstraints(lp_constraints)
			lpmodel.doplanning(True)
			
			new_output_to_acheive = lpmodel.getoutput(output_object, 1, Core.FMToutputlevel.standard)

			for key, value in new_output_to_acheive.items():
				if key in ["NA", "Total"] or value == 0:
					continue
			
				self.modelparser.redirectlogtofile(workspace + "/output.log")
				strategic, stochastic, tactic = self.create_replanning_models()	

				self.Logging.log_message("INFO",
					f"Setting new target value for output {output}. Difference of "
					f"{output_results[output][key] - new_output_to_acheive[key]} "	
					f"based on previous iteration results.")		
				output_results[output] = new_output_to_acheive

				# On ajoute la nouvelle fonction objective au modèle stratégique
				constraints = strategic.getconstraints()
				constraints[0] = new_objective
				strategic.setconstraints(constraints)

				self.Logging.log_message("INFO", 
						f"Finding max factor for target value {value} for key {key}.")

				for model in [strategic, stochastic, tactic]:
					self._change_area(model, key)

				best_factor = self._find_factor(
					strategic,
					stochastic,
					tactic,
					output,
					key,
					value,
					Path(workspace),
					threads, 
					known_values)

				self.Logging.log_message("INFO", 
						f"Best factor found for output {output} and key {key} is {best_factor:.2f}.")

				if output not in final_values:
					final_values[output] = {key: {'value': value, 'factor': best_factor}}
				else:
					final_values[output][key] = {'value': value, 'factor': best_factor}
		
		self.Logging.log_message("INFO", 
			f"Final results: {final_values}")
	
		return final_values

if __name__ == "__main__":
	path = Path("C:\\Users\\Admlocal\\Documents\\issues\\modele_vanille\\CC_modele_feu\\CC_V2\\Mod_cc_v2.pri")
	scenarios = ["strategique_vanille", "stochastique_sans_feu", "tactique_vanille"]
	model = ModelParser(path, scenarios, 20, logger_suffix="_original")

	# OVOLGRREC, OVOLGFREC 
	# Exemple de known_values à passer à find_max_value
	known_values = {
		"OVOLTOTREC": {"09351": {"min": 0.86, "max": 0.87}
		},
	}

	output_list = [
		#"OVOLTOTREC", 
		"OSUPREALNET_ACT", 
		"OSUPREALEPC", 
		"OSUPREALREGAEDU_BR", 
		"OSUPREALEC",
		"OSUPREALEC_BR",
		"OSUPREALPL",
		"OSUPREALREG",
		"OSUPREALPL_BR",
		"OSUPPL_FEU_POSTRECUP",
		]
	
	results = model.find_max_values_with_obj(output_list, "C:/Users/Admlocal/Documents/SCRAP1",  threads=5)
