import sys
import socket
import threading
import time
import argparse
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *

class MasterServer:
    def __init__(self, host, portC=None, portS=None):
        self.host = host
        self.portC = portC
        self.portS = portS
        self.server_socket_client = None
        self.server_socket_slave = None
        self.clients = {}  # Associer les sockets clients et leurs adresses
        self.slaves = {}  # Associer les sockets slaves et leurs compteurs de tâches
        self.slave_ids = {}  # Associer un identifiant unique au slave
        self.client_slave_map = {}  # Associer chaque client à un slave
        self.lock = threading.Lock()  # Verrou pour la gestion des ressources partagées
        self.next_slave_id = 1  # Initialiser le numéro du slave

    def Start(self):
        try:
            # Création des sockets
            self.server_socket_client = socket.socket()
            self.server_socket_client.bind((self.host, self.portC))
            self.server_socket_client.listen(5)
            print(f"Écoute maître <==> client {self.host}:{self.portC}")

            self.server_socket_slave = socket.socket()
            self.server_socket_slave.bind((self.host, self.portS))
            self.server_socket_slave.listen(5)
            print(f"Écoute maître <==> slave {self.host}:{self.portS}")

            # Threads pour gérer les connexions
            threading.Thread(target=self.accept_Client, daemon=True).start()
            threading.Thread(target=self.accept_Slave, daemon=True).start()

            print("Serveur maître en attente de connexions...")
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nArrêt du serveur maître.")
        except Exception as e:
            print(f"Erreur lors du démarrage : {e}")
        finally:
            if self.server_socket_client:
                self.server_socket_client.close()
            if self.server_socket_slave:
                self.server_socket_slave.close()

    def accept_Client(self):
        while True:
            client_socket, client_address = self.server_socket_client.accept()
            self.clients[client_socket] = client_address
            print(f"Client connecté : {client_address}")

            try:
                # Trouver un slave disponible immédiatement
                slave_socket = self.get_least_busy_slave()

                # Associer le client à un slave
                self.client_slave_map[client_socket] = slave_socket
                with self.lock:
                    self.slaves[slave_socket] += 1  # Incrémenter le compteur de tâches pour le slave

                # Gérer la communication avec le client et le slave
                threading.Thread(target=self.handle_client, args=(client_socket, slave_socket), daemon=True).start()

            except ValueError as e:
                print(f"Aucun slave disponible pour le client {client_address} : {e}")
                client_socket.close()

    def accept_Slave(self):
        while True:
            slave_socket, slave_address = self.server_socket_slave.accept()
            self.slaves[slave_socket] = 0  # Initialiser le compteur de tâches pour ce slave
            slave_id = self.next_slave_id  # Attribuer un identifiant unique
            self.slave_ids[slave_socket] = slave_id  # Associer l'identifiant au slave
            self.next_slave_id += 1  # Incrémenter pour le prochain slave
            print(f"Slave {slave_id} connecté : {slave_address}")
            threading.Thread(target=self.handle_slave, args=(slave_socket,), daemon=True).start()

    def get_least_busy_slave(self):
        with self.lock:
            # Trouver le slave avec le compteur de tâches le plus bas
            available_slaves = [sock for sock, count in self.slaves.items() if count < 5]
            if not available_slaves:
                raise ValueError("Aucun slave disponible.")
            # Retourner le slave avec le compteur le plus bas
            return min(available_slaves, key=lambda slave: self.slaves[slave])

    def handle_client(self, client_socket, slave_socket):
        try:
            client_address = self.clients[client_socket]
            print(f"Gestion du client {client_address} avec le slave {self.slaves[slave_socket]}")

            while True:
                # Réception du nom de fichier
                file_name = client_socket.recv(1024).decode()
                if not file_name:  # Si le client ferme la connexion
                    print(f"Le client {client_address} a terminé ou fermé la connexion.")
                    break

                print(f"Nom de fichier reçu du client {client_address} : {file_name}")
                
                # Envoi du nom du fichier au slave
                slave_socket.send(file_name.encode())
                print(f"Nom de fichier '{file_name}' envoyé au slave {self.slaves[slave_socket]}")

                # Réception et transfert du fichier
                file_data = self.receive_file(client_socket)
                if file_data:
                    self.send_file_to_slave(file_data, slave_socket)

            # Une fois le client terminé, libérer le slave et démarrer la dissociation
            self.remove_client(client_socket)
            with self.lock:
                self.slaves[slave_socket] -= 1  # Décrémenter le compteur de tâches du slave
                print(f"Task libérée pour le slave {slave_socket.getpeername()}.")

            # Dissocier le client du slave
            self.client_slave_map.pop(client_socket, None)

        except Exception as e:
            print(f"Erreur avec le client {client_socket}: {e}")

    def handle_slave(self, slave_socket):
        try:
            slave_address = self.slaves[slave_socket]
            print(f"Gestion des messages du slave {slave_address}")
            
            while True:
                # Réception du message du slave
                message = slave_socket.recv(1024).decode()
                if not message:
                    break
                
                print(f"Message du slave {slave_address} : {message}")

                # Rechercher le client associé au slave
                client_socket = self.get_client_for_slave(slave_socket)
                if not client_socket:
                    print("Aucun client associé au slave.")
                    continue  

                # Si le message indique que le traitement est en cours
                if "fichier en cours de traitement" in message:
                    client_socket.sendall(message.encode())
                    print(f"Message '{message}' envoyé au client {self.clients[client_socket]}")
                                
                # Si le message indique la fin du traitement du fichier
                elif "Fin de traitement du fichier" in message:
                    # Décrémenter la tâche du slave et libérer la tâche
                    with self.lock:
                        self.slaves[slave_socket] = 0  # Réinitialisation du compteur de tâches
                        print(f"Fin du traitement pour le slave {slave_socket.getpeername()}. Tâches restantes: {self.slaves[slave_socket]}")
                    self.send_result_to_client(client_socket, message)

        except Exception as e:
            print(f"Erreur avec le slave {slave_socket}: {e}")

    def get_client_for_slave(self, slave_socket):
        for client_socket, slave in self.client_slave_map.items():
            if slave == slave_socket:
                return client_socket
        return None

    def receive_file(self, client_socket):
        file_data = b""
        while True:
            chunk = client_socket.recv(1024)
            if not chunk or chunk.decode(errors="ignore") == "fin de transfert":
                print("Fin de transfert détectée.")
                break
            file_data += chunk
        print(f"Fichier reçu ({len(file_data)} octets)")
        return file_data

    def send_file_to_slave(self, file_data, slave_socket):
        for i in range(0, len(file_data), 1024):
            slave_socket.send(file_data[i:i+1024])
        slave_socket.send("fin de transfert".encode())
        print("Fichier envoyé au slave.")

    def send_result_to_client(self, client_socket, message):
        # Ici, "message" contient déjà la réponse complète
        result = message.replace("Fin de traitement du fichier", "").strip()  # Nettoyer si nécessaire

        # Envoi du résultat au client
        client_socket.sendall(result.encode())
        print(f"Résultat envoyé au client : {result}")

    def remove_client(self, client_socket):
        with self.lock:
            slave_socket = self.client_slave_map.pop(client_socket, None)
            if slave_socket:
                # Libérer une tâche du slave associé
                self.slaves[slave_socket] = max(0, self.slaves[slave_socket] - 1)
                print(f"Task libérée pour le slave {slave_socket.getpeername()}.")
        self.clients.pop(client_socket, None)
        client_socket.close()
        print(f"Client déconnecté.")

    def remove_slave(self, slave_socket):
        with self.lock:
            # Libérer les tâches associées au slave
            if slave_socket in self.slaves:
                task_count = self.slaves.pop(slave_socket)
                print(f"Slave {slave_socket.getpeername()} déconnecté. Tâches restantes : {task_count}.")
        slave_socket.close()
        print(f"Slave déconnecté.")

    def release_slave_task(self, slave_socket):
        with self.lock:
            if slave_socket in self.slaves:
                self.slaves[slave_socket] = max(0, self.slaves[slave_socket] - 1)
                print(f"Task libérée pour le slave {self.slaves[slave_socket]}.")

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception as e:
        print(f"Erreur lors de la récupération de l'IP locale : {e}")
        return "127.0.0.1"


class SlaveMonitorGUI(QMainWindow):
    def __init__(self, master_server):
        super().__init__()
        self.master_server = master_server
        self.setWindowTitle("Moniteur des Slaves")
        self.setGeometry(100, 100, 400, 300)

        # Configuration de l'interface
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.label = QLabel("Slaves Connectés et Charge de Travail :")
        self.layout.addWidget(self.label)

        self.slave_list_widget = QListWidget()
        self.layout.addWidget(self.slave_list_widget)

        # Mise à jour automatique
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_slave_list)
        self.timer.start(1000)  # Mise à jour toutes les secondes

    def update_slave_list(self):
        """Mise à jour de la liste des slaves connectés."""
        self.slave_list_widget.clear()
        with self.master_server.lock:
            for slave_socket, task_count in self.master_server.slaves.items():
                try:
                    slave_id = self.master_server.slave_ids.get(slave_socket, "Inconnu")
                    # Affichage de l'identifiant du slave et du nombre de tâches
                    self.slave_list_widget.addItem(f"Slave {slave_id} - Tâches: {task_count}")
                except OSError:
                    pass  # Évitez les erreurs si le socket est déconnecté


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serveur maître avec interface graphique.")
    parser.add_argument("--portC", type=int, required=True, help="Port pour les clients.")
    parser.add_argument("--portS", type=int, required=True, help="Port pour les slaves.")
    args = parser.parse_args()

    local_ip = get_local_ip()
    print(f"Adresse du serveur : {local_ip}")
    print(f"Port clients : {args.portC}")
    print(f"Port slaves : {args.portS}")

    # Initialisation du serveur
    server = MasterServer(host=local_ip, portC=args.portC, portS=args.portS)

    # Exécution du serveur dans un thread séparé
    threading.Thread(target=server.Start, daemon=True).start()

    # Lancement de l'interface graphique
    app = QApplication(sys.argv)
    gui = SlaveMonitorGUI(server)
    gui.show()
    sys.exit(app.exec())