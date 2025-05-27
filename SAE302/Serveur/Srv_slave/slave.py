import socket
import os
import subprocess
import argparse
import re



class Slave:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.slave_socket = None
        self.file_path = None  # Pour garder la trace du fichier reçu

    def connect_to_server(self):
        try:
            self.slave_socket = socket.socket()
            self.slave_socket.connect((self.host, self.port))
            print(f"Connecté au serveur {self.host}:{self.port}")
        except Exception as e:
            print(f"Erreur de connexion au serveur : {e}")
            exit(1)

    def receive_file_name(self):
        try:
            file_name = self.slave_socket.recv(1024).decode()
            print(f"Réception du nom du fichier : {file_name}")
            if file_name:
                file_name = file_name.replace("\r", "").replace("\n", "")
                self.slave_socket.send("fichier en cours de traitement".encode())
                print("fichier en cours de traitement")
                return file_name
        except Exception as e:
            print(f"Erreur lors de la réception du nom du fichier : {e}")

    def receive_file(self, file_name):
        try:
            self.file_path = os.path.join(os.getcwd(), file_name)
            with open(self.file_path, "wb") as file:
                while True:
                    data = self.slave_socket.recv(1024)
                    if len(data) < 1024:
                        if data:
                            file.write(data)
                        print("Fin de la réception détectée.")
                        break
                    file.write(data)
                    file.flush()
            print(f"Fichier {file_name} reçu avec succès à {self.file_path}.")
        except Exception as e:
            print(f"Erreur lors de la réception du fichier : {e}")

    def message_fin_transfer(self):
        try:
            message = self.slave_socket.recv(1024).decode()
            print(f"Message reçu du serveur : {message}")
            return message == "fin de transfert"
        except Exception as e:
            print(f"Erreur lors de la réception du message de fin de transfert : {e}")
            return False

    def execute_file(self, file_name):
        try:
            file_extension = os.path.splitext(file_name)[1]  # Extraction de l'extension du fichier
            print(f"Tentative d'exécution du fichier : {file_name} avec extension {file_extension}")
            
            # Traitement en fonction de l'extension du fichier
            if file_extension == ".py":
                return self.execute_python_file(file_name)
            elif file_extension == ".java":
                return self.execute_java_file(file_name)
            elif file_extension == ".c":
                return self.execute_c_file(file_name)
            elif file_extension == ".cpp":
                return self.execute_cpp_file(file_name)
            else:
                print(f"Extension de fichier {file_extension} non supportée.")
                return f"Erreur : Extension de fichier non supportée pour {file_name}"
        except Exception as e:
            print(f"Erreur lors de l'exécution du fichier : {e}")
            return f"Erreur lors de l'exécution du fichier : {e}"

    def execute_python_file(self, file_name):
        try:
            print("Execution en python")
            result = subprocess.run(
                ["python", file_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode == 0:
                print("Exécution réussie du fichier Python.")
                return result.stdout.strip()
            else:
                print(f"Erreur lors de l'exécution du fichier Python : {result.stderr.strip()}")
                return f"Erreur lors de l'exécution : {result.stderr.strip()}"
        except Exception as e:
            print(f"Erreur lors de l'exécution du fichier Python : {e}")
            return f"Erreur lors de l'exécution du fichier Python : {e}"



    def execute_java_file(self, file_name):
        try:
            print("Execution en Java")
            
            # Vérifier si le fichier existe
            file_path = os.path.join(os.getcwd(), file_name)
            print(f"Fichier à compiler : {file_path}")
            
            if not os.path.exists(file_path):
                print(f"Erreur : Le fichier {file_name} n'existe pas dans le répertoire {os.getcwd()}")
                return f"Erreur : Le fichier {file_name} n'existe pas"
            
            # Lire le fichier pour détecter le nom de la classe publique
            with open(file_path, 'r') as file:
                content = file.read()
            
            match = re.search(r'public\s+class\s+(\w+)', content)
            if not match:
                print("Erreur : Impossible de trouver une classe publique dans le fichier.")
                return "Erreur : Impossible de trouver une classe publique dans le fichier."
            
            class_name = match.group(1)
            print(f"Nom de la classe publique détectée : {class_name}")
            
            # Vérifier si le nom du fichier correspond à la classe publique
            expected_file_name = f"{class_name}.java"
            if file_name != expected_file_name:
                print(f"Renommage du fichier {file_name} en {expected_file_name}")
                os.rename(file_path, os.path.join(os.getcwd(), expected_file_name))
                file_path = os.path.join(os.getcwd(), expected_file_name)
                file_name = expected_file_name

            # Compiler le fichier Java
            compile_command = ['javac', file_path]
            print(f"Commande à exécuter : {' '.join(compile_command)}")
            compile_result = subprocess.run(compile_command, capture_output=True, text=True)
            
            if compile_result.returncode != 0:
                print(f"Erreur de compilation : {compile_result.stderr}")
                return f"Erreur de compilation : {compile_result.stderr}"
            
            print(f"Compilation réussie. Fichier classe généré : {class_name}.class")
            
            # Exécuter le fichier compilé
            run_command = ['java', class_name]
            print(f"Commande à exécuter : {' '.join(run_command)}")
            run_result = subprocess.run(run_command, capture_output=True, text=True)
            
            if run_result.returncode == 0:
                print("Exécution réussie du fichier Java.")
                output = run_result.stdout.strip()
            else:
                print(f"Erreur lors de l'exécution du fichier Java : {run_result.stderr.strip()}")
                output = f"Erreur lors de l'exécution du fichier Java : {run_result.stderr.strip()}"
            
            # Supprimer les fichiers générés
            try:
                class_file = f"{class_name}.class"
                if os.path.exists(class_file):
                    os.remove(class_file)
                    print(f"Fichier {class_file} supprimé avec succès.")
                
                if os.path.exists(file_path):
                    os.remove(file_path)  # Supprimer le fichier Java modifié
                    print(f"Fichier {file_path} supprimé avec succès.")
            except Exception as e:
                print(f"Erreur lors de la suppression des fichiers : {e}")

            return output
        
        except Exception as e:
            print(f"Erreur lors de l'exécution du fichier Java : {e}")
            return f"Erreur lors de l'exécution du fichier Java : {e}"


        
    def execute_c_file(self, file_name):
        try:
            print("Execution en C")

            # Vérifier si le fichier existe
            file_path = os.path.join(os.getcwd(), file_name)
            print(f"Fichier à compiler : {file_path}")
            
            if not os.path.exists(file_path):
                print(f"Erreur : Le fichier {file_name} n'existe pas dans le répertoire {os.getcwd()}")
                return f"Erreur : Le fichier {file_name} n'existe pas"

            # Nom de l'exécutable (on remplace les espaces par des underscores)
            exec_file = file_name.replace('.c', '_executable.exe').replace(' ', '_')
            print(f"Nom de l'exécutable généré : {exec_file}")
            file_path = os.path.join(os.getcwd(), file_name)  # Chemin absolu du fichier C
            print(f"nom du fichier natif normalement {file_path}")
            
            # Compiler le fichier C            
            compile_command = ['gcc', file_path, '-o', exec_file]
            print(f"Commande à exécuter : {' '.join(compile_command)}")
            compile_result = subprocess.run(compile_command, capture_output=True, text=True)

            # Vérifier si la compilation a échoué
            if compile_result.returncode != 0:
                print(f"Erreur de compilation : {compile_result.stderr}")
                return f"Erreur de compilation : {compile_result.stderr}"

            print(f"Compilation réussie. Fichier exécutable attendu : {exec_file}")

            # Vérifier si le fichier exécutable a été créé
            if not os.path.exists(exec_file):
                print(f"Erreur : Le fichier exécutable {exec_file} n'a pas été créé.")
                return f"Erreur : Le fichier exécutable {exec_file} n'a pas été créé."
            
            # Exécuter le fichier binaire
            result = subprocess.run([exec_file], capture_output=True, text=True)

            if result.returncode == 0:
                print("Exécution réussie du fichier C.")
                return result.stdout.strip()
            else:
                print(f" Erreur lors de l'exécution du fichier C : {result.stderr.strip()}")
                return f" Erreur lors de l'exécution du fichier C : {result.stderr.strip()}"

        except Exception as e:
            print(f" Erreur lors de l'exécution du fichier C : {e}")
            return f" Erreur lors de l'exécution du fichier C : {e}"



    def execute_cpp_file(self, file_name):
        try:
            print("Execution en C++")

            # Vérifier si le fichier existe
            file_path = os.path.join(os.getcwd(), file_name)
            print(f"Fichier à compiler : {file_path}")
            
            if not os.path.exists(file_path):
                print(f"Erreur : Le fichier {file_name} n'existe pas dans le répertoire {os.getcwd()}")
                return f"Erreur : Le fichier {file_name} n'existe pas"

            # Nom de l'exécutable (on remplace les espaces par des underscores)
            exec_file = file_name.replace('.cpp', '_executable.exe').replace(' ', '_')
            print(f"Nom de l'exécutable généré : {exec_file}")

            # Compiler le fichier C++ avec g++
            compile_command = ['g++', file_path, '-o', exec_file]
            print(f"Commande à exécuter : {' '.join(compile_command)}")
            compile_result = subprocess.run(compile_command, capture_output=True, text=True)

            # Vérifier si la compilation a échoué
            if compile_result.returncode != 0:
                print(f"Erreur de compilation : {compile_result.stderr}")
                return f"Erreur de compilation : {compile_result.stderr}"

            print(f"Compilation réussie. Fichier exécutable attendu : {exec_file}")

            # Vérifier si le fichier exécutable a été créé
            if not os.path.exists(exec_file):
                print(f"Erreur : Le fichier exécutable {exec_file} n'a pas été créé.")
                return f"Erreur : Le fichier exécutable {exec_file} n'a pas été créé."
            
            # Exécuter le fichier binaire
            result = subprocess.run([exec_file], capture_output=True, text=True)

            if result.returncode == 0:
                print("Exécution réussie du fichier C++.")
                return result.stdout.strip()
            else:
                print(f"Erreur lors de l'exécution du fichier C++ : {result.stderr.strip()}")
                return f"Erreur lors de l'exécution du fichier C++ : {result.stderr.strip()}"

        except Exception as e:
            print(f"Erreur lors de l'exécution du fichier C++ : {e}")
            return f"Erreur lors de l'exécution du fichier C++ : {e}"


    def send_result(self, result):
        try:
            if not result:
                result = "Aucun résultat à envoyer."

            # Ajouter un marqueur de fin avec un retour à la ligne pour le séparer
            result += "\nFin de traitement du fichier"

            # Envoyer le message complet
            self.slave_socket.sendall(result.encode())
            print("Résultat envoyé au serveur avec succès.")

        except Exception as e:
            print(f"Erreur lors de l'envoi des résultats : {e}")

    def delete_file(self):
        try:
            if self.file_path and os.path.exists(self.file_path):
                os.remove(self.file_path)
                print(f"Fichier {self.file_path} supprimé avec succès.")
        except Exception as e:
            print(f"Erreur lors de la suppression du fichier : {e}")

    def run(self):
        self.connect_to_server()
        while True:  # Boucle principale pour rester connecté
            file_name = self.receive_file_name()
            if file_name:
                self.receive_file(file_name)
                if self.message_fin_transfer():
                    result = self.execute_file(file_name)
                    self.send_result(result)
                    self.delete_file()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lancer un slave pour communiquer avec un serveur.")
    parser.add_argument("host", type=str, help="Adresse IP du serveur.")
    parser.add_argument("port", type=int, help="Port du serveur.")
    args = parser.parse_args()

    slave = Slave(host=args.host, port=args.port)
    slave.run()