import socket
import sys
import re
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *

class FileSenderThread(QThread):
    result_signal = pyqtSignal(str)

    def __init__(self, client_socket, file_path, file_content, parent=None):
        super().__init__(parent)
        self.client_socket = client_socket
        self.file_path = file_path
        self.file_content = file_content

    def run(self):
        try:
            if not self.file_path:
                raise ValueError("Aucun fichier sélectionné.")
            if not self.file_content.strip():
                raise ValueError("La zone de texte est vide.")

            # Envoi du nom du fichier
            file_name = self.file_path.split('/')[-1]
            print(f"Envoi du nom du fichier : {file_name}")  # Log
            self.client_socket.send(file_name.encode())

            # Attente de la confirmation du serveur
            confirmation = self.client_socket.recv(1024).decode()
            print(f"Confirmation reçue du serveur : {confirmation}")  # Log
            self.result_signal.emit("Le contenu est en cours de traitement...")

            if confirmation == "fichier en cours de traitement":
                # Envoi du contenu de la zone de texte par morceaux
                print("Envoi du contenu de la zone de texte.")  # Log
                content_bytes = self.file_content.encode()  # Encodage en bytes
                chunks = [content_bytes[i:i+1024] for i in range(0, len(content_bytes), 1024)]

                for chunk in chunks:
                    self.client_socket.send(chunk)

                # Envoi d'un indicateur de fin
                print("Envoi du message de fin d'envoi.")
                self.client_socket.send("fin de transfert".encode())

                # Recevoir le résultat du serveur
                result = ""
                while True:
                    chunk = self.client_socket.recv(1024).decode()
                    if chunk == "fin de transfert":  # Si le paquet reçu est le message de fin
                        print("Fin de transfert reçue.")
                        break
                    result += chunk
                    if len(chunk) < 1024:
                        print("Dernier paquet de résultat reçu.")
                        break

                print(f"Résultat complet reçu du serveur : {result}")
                self.result_signal.emit(result)  # Afficher le résultat dans la zone de texte

            else:
                raise ValueError("Le serveur n'a pas confirmé la réception du fichier.")

        except Exception as e:
            self.result_signal.emit(f"Erreur : {str(e)}")


class FirstWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Définition des widgets pour l'interface graphique
        widget = QWidget()
        self.setCentralWidget(widget)
        grid = QGridLayout()
        widget.setLayout(grid)

        grid.setSpacing(0)
        
        self.setWindowTitle("Client")
        self.setGeometry(100, 100, 400, 200)

        # label et ligne pour donner l'ip du server
        self.label_ip_server = QLabel("IP du Server")
        self.ip_server = QLineEdit("")

        # label et ligne pour donner le port du server
        self.label_port_server = QLabel("Port du server")
        self.port_server = QLineEdit("")

        # Bouton de connection au server
        self.login_bouton = QPushButton("Connection serveur")
        self.login_bouton.clicked.connect(self.login_Server)

        grid.addWidget(self.label_ip_server, 0, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.ip_server, 1, 0,)
        grid.addWidget(self.label_port_server, 2, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.port_server, 3, 0)
        grid.addWidget(self.login_bouton, 4, 0)


    def validate_ip(self, ip):
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(pattern, ip):
            return all(0 <= int(octet) <= 255 for octet in ip.split('.'))
        return False

    def erreur(self, message):
        QMessageBox.critical(self, "Erreur", message)

    def login_Server(self):
        host = self.ip_server.text()
        port = self.port_server.text()

        # Validation de l'IP
        if not self.validate_ip(host):
            self.erreur("L'adresse IP n'est pas valide. Exemple de format : xxx.xxx.xxx.xxx")
            return

        # Validation du port
        try:
            port = int(port)
            if not (1 <= port <= 65535):
                raise ValueError("Port invalide")
        except ValueError:
            self.erreur("Le port doit être un entier valide entre 1 et 65535.")
            return

        try:
            # Tentative de connexion
            print(f"Tentative de connexion à {host}:{port}")
            client_socket = socket.socket()

            # On essaie de se connecter au serveur
            client_socket.connect((host, port))

            # Si la connexion réussit, on ouvre la deuxième fenêtre
            self.second_window = SecondWindow(client_socket)
            self.second_window.show()
            self.close()  

        except socket.error:
            # Erreur si la connexion échoue (par exemple si le serveur n'est pas lancé)
            self.erreur(f"Erreur de connexion. Vérifiez l'adresse IP et le port.")
        
        except ValueError:
            # Erreur liée au port
            self.erreur("Le port doit être un entier valide entre 1 et 65535.")
        
        except Exception as e:
            # Capturer toute autre exception non attendue
            self.erreur(f"Une erreur inattendue est survenue: {str(e)}")


class SecondWindow(QMainWindow):
    result_signal = pyqtSignal(str)

    def __init__(self, client_socket):
        super().__init__()
        self.client_socket = client_socket
        self.setWindowTitle("Client")
        self.setFixedSize(600, 400)

        widget = QWidget()
        self.setCentralWidget(widget)
        grid = QGridLayout()
        widget.setLayout(grid)

        self.search_file = QPushButton("Sélectionner un fichier", self)
        self.search_file.clicked.connect(self.select_file)

        self.switch_type_file = QComboBox()
        self.switch_type_file.addItems(["Python","Java","C","C++"])
        

        self.text_edit_code = QTextEdit(self)
        self.text_edit_code.setReadOnly(False)

        self.label_resultat = QLabel("Résultat du code envoyé")
        self.text_resultat = QTextEdit(self)
        self.text_resultat.setReadOnly(True)

        self.send_file = QPushButton("Envoyer le fichier")
        self.send_file.clicked.connect(self.send_File)

        self.deco_server = QPushButton("Se déconnecter du serveur")
        self.deco_server.clicked.connect(self.deco_Server)

        grid.addWidget(self.switch_type_file,0,0)
        grid.addWidget(self.search_file, 1,0)
        grid.addWidget(self.text_edit_code, 2, 0, 5, 1)
        grid.addWidget(self.label_resultat, 7, 0)
        grid.addWidget(self.text_resultat, 8, 0, 5, 1)
        grid.addWidget(self.send_file, 14, 0)
        grid.addWidget(self.deco_server, 15, 0)


        self.result_signal.connect(self.update_result)

# fonction pour metre à jour la zone de résultat
    def update_result(self, result):
        """ Slot pour mettre à jour le résultat dans le QTextEdit """
        print(f"Résultat à afficher : {result}")  # Ajouter ce print pour déboguer
        self.text_resultat.setText(result)  # Met à jour le QTextEdit

# fonction pour vérifier la selection d'un fichier 
    def send_File(self):
        # Vérifiez si un fichier a été sélectionné
        if not hasattr(self, 'file_path'):
            self.error("Aucun fichier sélectionné.")
            return
        
        # Récupérez le contenu de la zone de texte
        file_content = self.text_edit_code.toPlainText()
        if not file_content.strip():
            self.error("La zone de texte est vide. Veuillez entrer du contenu à envoyer.")
            return

        # Lancez le thread pour envoyer le nom du fichier et le contenu de la zone de texte
        self.file_sender_thread = FileSenderThread(self.client_socket, self.file_path, file_content)
        self.file_sender_thread.result_signal.connect(self.update_result)
        self.file_sender_thread.start()


    def select_file(self):
        """Ouvre une boîte de dialogue pour sélectionner un fichier selon le type choisi"""
        file_type = self.switch_type_file.currentText()

        if file_type == "Python":
            file_path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un fichier Python", "", "Fichiers Python (*.py);;Tous les fichiers (*)")
        elif file_type == "Java":
            file_path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un fichier Java", "", "Fichiers Java (*.java);;Tous les fichiers (*)")
        elif file_type == "C":
            file_path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un fichier C", "", "Fichiers C (*.c);;Tous les fichiers (*)")
        elif file_type == "C++":
            file_path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un fichier C++", "", "Fichiers C++ (*.cpp);;Tous les fichiers (*)")

        if file_path:
            self.search_File(file_path)


    def search_File(self, file_path):
        """Fonction pour ouvrir un fichier et afficher son contenu dans un QTextEdit"""
        if file_path:
            try:
                # Si un fichier est sélectionné, on l'ouvre et affiche son contenu dans QTextEdit
                with open(file_path, "r") as file:
                    content = file.read()
                    self.text_edit_code.setText(content)  # Affiche le contenu du fichier dans QTextEdit
                    self.file_path = file_path  # Enregistre le chemin du fichier
            except Exception as e:
                self.error(f"Problème survenu durant l'ouverture du fichier : {e}")

# fonction pour chercher les fichier python 
    def search_File(self,file_path):
        # Ouvrir une boîte de dialogue pour choisir un fichier

        if file_path:
            try: 
                # Si un fichier est sélectionné, on l'ouvre et affiche son contenu dans le QTextEdit
                with open(file_path, "r") as file:
                    content = file.read()
                    self.text_edit_code.setText(content)  # Affiche le contenu du fichier dans QTextEdit
                    self.file_path = file_path
            except Exception as e:
                self.error(f"Problème survenu durant l'ouverture du fichier : {e}")


# fonction pour créé un page d'erreur
    def error(self, message):
        err_dialog = QMessageBox(self)
        err_dialog.setIcon(QMessageBox.Icon.Critical)
        err_dialog.setWindowTitle("Erreur")
        err_dialog.setText(message)
        err_dialog.exec()

# fonction pour le bouton de déconnection au serveur
    def deco_Server(self):
        try:
            if self.client_socket:
                self.client_socket.close()
                print("Déconnexion du serveur.")

            # Ferme la fenêtre actuelle avant d'ouvrir la première fenêtre
            self.close()

            # Crée et affiche la première fenêtre dans le thread principal
            self.first_window = FirstWindow()
            self.first_window.show()

        except Exception as e:
            self.error(f"Erreur lors de la déconnexion : {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FirstWindow()
    window.show()
    sys.exit(app.exec())