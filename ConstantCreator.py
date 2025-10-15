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
    
    def create_constant_file(self):
        output_dict = self.get_outputs(0, self.output_dict)

        vielles_foret = []
        entente = []

        for output, value in output_dict.items():
            for key, name in self.output_name.items():
                if key.upper() in output.upper():
                    for theme, result in value.items():
                        if key.startswith("Sup"):
                                vielles_foret.append(f"{name}({theme}) {result}\n")
                        if key.startswith("OSUP"):
                                entente.append(f"{name}({theme}) {result}\n")

        with open("C:\\Users\\Admlocal\\Documents\\SCRAP\\ViellesForet.con", "w") as file:
            file.writelines(vielles_foret)

        with open("C:\\Users\\Admlocal\\Documents\\SCRAP\\Entente.con", "w") as file:
            file.writelines(entente)


if __name__ == "__main__":
    path = Path("T:\\Donnees\\02_Courant\\07_Outil_moyen_methode\\01_Entretien_developpement\\Interne\\FMT\\Entretien\\Modeles_test\\02661\\PC_9307_U02661_4_Vg2_2023_vRP1f.pri")
    parser = ConstantCreator(path, ["14_Sc5_Determin_apsp"], 1)
    parser.create_constant_file()
