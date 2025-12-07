public class TestJavaIssues {

    public static void printLength(String name) {
        System.out.println(name.length());  // can cause NullPointerException
    }

    public static void main(String[] args) {
        printLength(null);  // crash
    }
}
