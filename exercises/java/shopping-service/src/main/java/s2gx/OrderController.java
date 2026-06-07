package s2gx;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/orders")
public class OrderController {

    private final OrderRepository orderRepository;

    public OrderController(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    @GetMapping
    public List<Order> index(@RequestParam(defaultValue = "10") int max) {
        return orderRepository.findAll().stream()
                .limit(Math.min(max, 100))
                .toList();
    }

    @GetMapping("/{id}")
    public ResponseEntity<Order> show(@PathVariable Long id) {
        return orderRepository.findById(id)
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<Order> save(@RequestBody Order order) {
        Order saved = orderRepository.save(order);
        return ResponseEntity.status(HttpStatus.CREATED).body(saved);
    }

    @PutMapping("/{id}")
    public ResponseEntity<Order> update(@PathVariable Long id, @RequestBody Order order) {
        return orderRepository.findById(id)
                .map(existing -> ResponseEntity.ok(orderRepository.save(order)))
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        return orderRepository.findById(id)
                .map(order -> {
                    orderRepository.delete(order);
                    return ResponseEntity.<Void>noContent().build();
                })
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    // Switch expression maps domain status to HTTP semantics
    private HttpStatus toHttpStatus(OrderStatus status) {
        return switch (status) {
            case PENDING, CONFIRMED -> HttpStatus.ACCEPTED;
            case SHIPPED, DELIVERED -> HttpStatus.OK;
            case CANCELLED          -> HttpStatus.GONE;
        };
    }
}
