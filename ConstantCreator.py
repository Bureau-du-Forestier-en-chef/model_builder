from ModelParser import ModelParser
from pathlib import Path

class ConstantCreator(ModelParser):
    def __init__(self, path, scenario, length):
        super().__init__(path, scenario, length)
        self.output_name = {
            "SupJeuneAlerte": "SupJeuneAlerte", 
            "SupJeuneAccept": "SupJeuneAccept", 
            "SupVieuxAlerte": "SupVieuxAlerte", 
            "SupVieuxAccept": "SupVieuxAccept", 
            "OSUPREGECOUTA": "SupProdUta", 
            "OSUPREGECO_HARAT": "SupProdEnrqc", 
            "OSUPREGECO_HARTIF": "SupProdTIF"
            }
        self.output_path = self._get_file_path(".out")
        self.output_dict = self._iter_output()

    def _iter_output(self):
        if self.output_path is None:
            raise Exception("No output file found")
        
        output_name = []
        with open(self.output_path, "r") as file:
            lines = file.readlines()
            for line in lines:
                line_splited = line.strip().split()
                if len(line_splited) == 0 or line_splited[0] != "*OUTPUT":
                    continue
                else:
                    for element in self.output_name.keys():
                        if element.upper() in line_splited[1].upper():
                            output_name_split = line_splited[1].split("(")
                            output_name.append(output_name_split[0])
        
        return output_name
    
    def create_constant_file(self, output_path=None):
        output_dict = self.get_outputs_results(0, self.output_dict)

        if output_path:
            base_path = Path(output_path)
        else:
            base_path = self.path.parent

        files = {
            "Sup": base_path / "ViellesForet.con",
            "OSUP": base_path / "Entente.con",
        }

        contents = {prefix: [] for prefix in files}

        for output, value in output_dict.items():
            for key, name in self.output_name.items():
                if key.upper() not in output.upper():
                    continue

                prefix = next((p for p in files if key.startswith(p)), None)
                if prefix is None:
                    raise ValueError(f"Unknown prefix for output {output}")
                for theme, result in value.items():
                    if theme in {"NA", "Total"}:
                        continue
                    contents[prefix].append(f"{name}({theme}) {round(result, 1)}\n")

                contents[prefix].append("\n")

        for prefix, path in files.items():
            with path.open("w", encoding="utf-8") as f:
                f.writelines(contents[prefix])


if __name__ == "__main__":
    path = Path("T:\\Donnees\\02_Courant\\07_Outil_moyen_methode\\01_Entretien_developpement\\Interne\\FMT\\Entretien\\Modeles_test\\02661\\PC_9307_U02661_4_Vg2_2023_vRP1f.pri")
    parser = ConstantCreator(path, ["14_Sc5_Determin_apsp"], 1)
    parser.create_constant_file(output_path="C:/Users/Admlocal/Documents/SCRAP")
