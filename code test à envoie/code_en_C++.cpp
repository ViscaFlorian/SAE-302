#include <iostream>
#include <thread>  // Pour utiliser sleep_for
#include <chrono>  // Pour utiliser chrono::seconds

using namespace std;

int main() {
    cout << "Hello, World!" << endl;

    // Attendre 30 secondes
    this_thread::sleep_for(chrono::seconds(30));

    cout << "30 secondes se sont écoulées." << endl;
    return 0;
}
