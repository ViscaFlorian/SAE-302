import time

def effectuer_calcul(a, b):
    """
    Effectue un calcul simple entre deux nombres.
    """
    time.sleep(5)
    somme = a + b
    produit = a * b
    return somme, produit

# Exemple d'utilisation
if __name__ == "__main__":
    a = 5
    b = 3
    somme, produit = effectuer_calcul(a, b)
    print(f"Somme de {a} et {b} : {somme}\n")
    print(f"Produit de {a} et {b} : {produit}\n")