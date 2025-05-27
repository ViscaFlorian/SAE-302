public class HelloWorld {
    public static void main(String[] args) {
        try {
            System.out.println("Hello, World!");
            // Ajouter un délai de 5 secondes (5000 millisecondes)
            Thread.sleep(5000);
            System.out.println("5 secondes se sont écoulées.");
        } catch (InterruptedException e) {
            System.out.println("Le délai a été interrompu.");
        }
    }
}
