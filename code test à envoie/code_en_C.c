#include <stdio.h>
#include <unistd.h>  // Pour utiliser sleep

int main() {
    printf("TDM-GCC fonctionne correctement!\n");

    // Attendre 30 secondes
    sleep(30);

    printf("30 secondes se sont écoulées.\n");

    return 0;
}
