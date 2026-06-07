package s2gx;

public record Customer(Long id, String name) {

    public Customer {
        if (name == null || name.isBlank())
            throw new IllegalArgumentException("name must not be blank");
    }

    @Override
    public String toString() { return name; }
}
