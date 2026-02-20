// CartSaga.java
package com.example.cart.saga;

import com.example.cart.event.CartSubmittedEvent;
import com.example.cart.saga.commands.ApplyPromotionsCommand;
import com.example.cart.saga.commands.ProcessPaymentCommand;
import com.example.cart.saga.commands.ReserveInventoryCommand;
import io.eventuate.tram.sagas.orchestration.SagaManager;
import org.springframework.stereotype.Component;

@Component
public class CartSaga {
    private final SagaManager<CartSagaData> sagaManager;

    public CartSaga(SagaManager<CartSagaData> sagaManager) {
        this.sagaManager = sagaManager;
    }

    @SagaStart
    public void handle(CartSubmittedEvent event) {
        CartSagaData data = new CartSagaData(
                event.getUserId(),
                event.getItems(),
                System.currentTimeMillis()
        );

        sagaManager.begin(
                data,
                new ReserveInventoryCommand(event.getItems()),
                new ApplyPromotionsCommand(event.getItems())
        );
    }

    @SagaEventHandler
    public void onInventoryReserved(InventoryReservedEvent event) {
        sagaManager.continueSaga(
                event.getSagaId(),
                new ProcessPaymentCommand(event.getUserId(), event.getTotalAmount())
        );
    }

    @SagaEventHandler
    public void onPaymentProcessed(PaymentProcessedEvent event) {
        sagaManager.endSaga(event.getSagaId());
    }

    @SagaEventHandler
    public void onInventoryReservationFailed(InventoryReservationFailedEvent event) {
        sagaManager.abortSaga(event.getSagaId());
    }
}