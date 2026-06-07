package s2gx;

import java.math.BigDecimal;

public record Product(String name, BigDecimal price) {

    public Product {
        if (name == null || name.isBlank())
            throw new IllegalArgumentException("name must not be blank");
        if (price.compareTo(BigDecimal.ZERO) < 0)
            throw new IllegalArgumentException("price must not be negative");
    }

    @Override
    public String toString() { return name; }
}
