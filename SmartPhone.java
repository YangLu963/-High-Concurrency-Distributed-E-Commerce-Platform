class Smartphone {
    private String brand;
    private String color;
    private double batterylevel;

    // Constructor
    Smartphone(String brand, String color) {
        this.brand = brand;
        this.color = color;
        this.batterylevel = 100; // 初始电量 100%
    }

    // 使用手机
    void use(int hours) {
        batterylevel -= 10 * hours;
        batterylevel = Math.max(batterylevel, 0);
        System.out.println(brand + " " + color + " used for " + hours + "h, battery = " + (int)batterylevel + "%");
    }

    // 充电
    void charge(double amount) {
        batterylevel += amount;
        batterylevel = Math.min(batterylevel, 100);
        System.out.println(brand + " " + color + " charged, battery = " + (int)batterylevel + "%");
    }

    // 显示信息
    void displayInfo() {
        System.out.println("Phone Info, Brand: " + brand + ", Color: " + color + ", Battery: " + (int)batterylevel + "%");
    }
}

public class SmartPhone {
    public static void main(String[] args) {
        Smartphone p1 = new Smartphone("iPhone", "Black");
        Smartphone p2 = new Smartphone("Samsung", "Blue");

        p1.use(3);
        p1.displayInfo();

        p2.charge(10);
        p2.displayInfo();
    }
}
