"""
class FactorIterator():
    def __init__(self):
        pass

    def _inspect_csv(self, output_name: str, id_type: str, value: float, field_path: str | Path) -> tuple[bool, str]:
		field_file = Path(field_path) / f"{self.scenarios[2]}.csv"
		is_valid = True
		TOLERANCE = 1
		msg = "Output value meets the required threshold at this time."

		if not field_file.exists():
			raise FileNotFoundError(f"Field file not found: {field_file}")

		for line in field_file.read_text().splitlines():
			line_splited = line.strip().split(";")
			if line_splited[2] == output_name and line_splited[3].strip('"') == id_type:
				# J'ai ajouté +1 pour éviter les problèmes d'arrondi flottant
				if float(line_splited[-1]) + TOLERANCE < value:
					is_valid = False
					msg = (f"Output {output_name} for id {id_type} has value {line_splited[-1]}, "
							f"which is less than the required value {value}.")
					break 
		return is_valid, msg
	
    def _find_factor(self, 
			strategic: Models.FMTlpmodel,
			stochastic: Models.FMTnssmodel,
			tactic: Models.FMTlpmodel,
			output: str,
			key: str,
			value: float,
			workspace: str,
			threads: int = 1,
			known_values: dict | None = None) -> float:
		
		factor_min = 0
		factor_max = 100
		
		if known_values and output in known_values and key in known_values[output]:
			factor_min = int(known_values[output][key]['min'] * 100)
			factor_max = int(known_values[output][key]['max'] * 100)
			self.Logging.log_message("INFO", 
					(f"Using known factor {known_values[output][key]} for output {output} and key {key}."))

		iterations = 0

		while (factor_max - factor_min) > 1 and iterations <= 8:
			factor_tested = ((factor_min + factor_max) // 2) / 100
			
			#monitor = LiveCSVMonitor(
			#	csv_path=Path(workspace) / f"{self.scenarios[2]}.csv",
			#	check_function=lambda: self._inspect_csv(
			#		output_name=output,
			#		id_type=key,
			#		value=value * factor_tested,
			#		field_path=workspace),
			#	logger=self.path.stem + ".log")
			#monitor.start()

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
				
			except MonitoredReplanningAbort as abort_error:
				factor_max = factor_tested * 100
				self.Logging.log_message("WARNING", 
							(f"Stopping factor search due to monitoring abort: {abort_error}. "
							f"Reducing max factor to {factor_max / 100:.2f}.")
						)
				
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
				is_valid, msg = self._inspect_csv(output, key, value * factor_tested, workspace)
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
				#monitor.stop()	
		
		return factor_min / 100

	def _change_area(self, model, key: str):
		area_to_keep = []
		for area in model.getarea():
			if key in str(area):
				area_to_keep.append(area)
		model.setarea(area_to_keep)

	def find_max_value(self, 
			output_results: dict,
			workspace: str = "C:/Users/Admlocal/Documents/SCRAP1", 
			threads: int = 1, 
			known_values: dict | None = None) -> dict:
		if len(self.models) < 3:
			raise Exception("Models for strategic, stochastic and tactic are required")
		
		final_values = {}
		for output, results in output_results.items():
			for key, value in results.items():
				if value == 0:
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
					workspace,
					threads, 
					known_values)
				
				self.Logging.log_message("INFO", 
						f"Best factor found for output {output} and key {key} is {best_factor:.2f}.")

				if output not in final_values:
					final_values[output] = {key: best_factor}
				else:
					final_values[output][key] = best_factor
	
		return final_values	
"""