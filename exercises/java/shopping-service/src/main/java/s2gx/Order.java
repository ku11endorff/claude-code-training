package s2gx;

import java.text.NumberFormat;
import java.util.List;

public record Order(String number, Customer customer, List<OrderLine> orderLines, OrderStatus status) {

    public Order {
        orderLines = List.copyOf(orderLines);
    }

    public double price() {
        return orderLines.stream()
                .mapToDouble(OrderLine::price)
                .sum();
    }

    public String statusDescription() {
        return switch (status) {
            case PENDING   -> "Awaiting confirmation";
            case CONFIRMED -> "Confirmed, preparing shipment";
            case SHIPPED   -> "In transit";
            case DELIVERED -> "Delivered";
            case CANCELLED -> "Cancelled";
        };
    }

    @Override
    public String toString() {
        NumberFormat nf = NumberFormat.getCurrencyInstance();
        return "#%s: %d lines, total %s [%s]".formatted(
                number, orderLines.size(), nf.format(price()), statusDescription());
    }
}
