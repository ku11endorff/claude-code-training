package s2gx;

import java.util.Optional;

public record OrderLine(Product product, int quantity) {

    public OrderLine {
        if (quantity < 0)
            throw new IllegalArgumentException("quantity must not be negative");
    }

    public double price() {
        return Optional.ofNullable(product)
                .map(p -> quantity * p.price().doubleValue())
                .orElse(0.0);
    }

    @Override
    public String toString() {
        return "%d %s @ %s = %.2f".formatted(quantity, product, product.price(), price());
    }
}
