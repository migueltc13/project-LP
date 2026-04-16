import unittest
import glob
import os
from src.lexer import lexer
from src.preprocessor import preprocess


# Run: python -m unittest tests/test_lexer.py
class TestFortranExamples(unittest.TestCase):

    def run_lexer_on_file(self, filepath, fmt):
        with open(filepath, 'r') as f:
            content = f.read()
        
        try:
            processed_code = preprocess(content, format=fmt)
        except Exception as e:
            self.fail(f"Erro a processar {filepath}: {e}")

        lexer.input(processed_code)
        
        tokens = []
        try:
            for tok in lexer:
                tokens.append(tok)
        except Exception as e:
            self.fail(f"Erro a processar {filepath}: {e}")
        
        return tokens

    # Testa se ficheiros .f geram tokens válidos
    def test_fixed_format_examples(self):
        files = glob.glob("examples/*.f") 
        if not files:
            self.skipTest("Nenhum ficheiro .f encontrado.")
            
        for filepath in files:
            with self.subTest(filename=os.path.basename(filepath)):
                tokens = self.run_lexer_on_file(filepath, "fixed")
                self.assertTrue(len(tokens) > 0, f"O ficheiro {filepath} não gerou nenhum token.")

    # Testa se ficheiros .f90 geram tokens válidos
    def test_free_format_examples(self):
        files = glob.glob("examples/*.f90")
        if not files:
            self.skipTest("Nenhum ficheiro .f90 encontrado.")
            
        for filepath in files:
            with self.subTest(filename=os.path.basename(filepath)):
                tokens = self.run_lexer_on_file(filepath, "free")
                self.assertTrue(len(tokens) > 0, f"O ficheiro {filepath} não gerou nenhum token.")

if __name__ == "__main__":
    unittest.main()