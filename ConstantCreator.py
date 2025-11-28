from pathlib import Path
from ModelParser import ModelParser

class ConstantCreator(ModelParser):
    """_summary_

    Args:
        ModelParser (_type_): _description_
    """
    def __init__(self, path, scenario, length):
        super().__init__(path, scenario, length)
        self.output_name = {
            "SupJeuneAlerte": "SupJeuneAlerte", 
            "SupJeuneAccept": "SupJeuneAccepte", 
            "SupVieuxAlerte": "SupVieuxAlerte", 
            "SupVieuxAccept": "SupVieuxAccepte", 
            "OSUPREGECOUTA": "SupProdUta", 
            "OSUPREGECO_HARAT": "SupProdEnrqc", 
            "OSUPREGECO_HARTIF": "SupProdTIF"
            }
        self.output_path = self._get_file_path(".out")
        self.output_name_list = [i.upper() for i in self.output_name.keys()]
        self.output_object = self._get_outputs_objects(self.output_name_list)

    def _get_outputs_objects(self, outputs: list[str]):
        output_objects = [
            output for output in self.lpmodel.getoutputs()
            if any(name in output.getname() for name in outputs)
        ]

        return output_objects

    def create_constant_file(self, output_path=None):
        output_dict = self.get_outputs_results(0, self.output_object)

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
    path = Path("C:\\Users\\Admlocal\\Documents\\issues\\modele_vanille\\CC_modele_feu\\CC_V2\\Mod_cc_v2.pri")
    parser = ConstantCreator(path, ["strategique_vanille"], 1)
    parser.create_constant_file(
        output_path="C:\\Users\\Admlocal\\Documents\\issues\\modele_vanille\\SCRAP")
