# Example Input: Anti-Duplicate Transfer Flow

## Source code / Logic snippet
```javascript
// Pseudocódigo del flujo lógico solicitado
async function handleTransferSubmission(transferData) {
    // 1. Validación de datos de entrada
    if (!transferData.amount || transferData.amount <= 0 || !transferData.destinationAccount) {
        return displayError("Datos de transferencia inválidos");
    }

    // 2. Pre-send Confirmation (Bloqueo de doble clic y renderizado de resumen)
    const userConfirmed = await renderConfirmationModal({
        target: transferData.destinationAccount,
        amount: transferData.amount,
        fee: calculateFee(transferData.amount)
    });

    if (!userConfirmed) {
        return cancelTransfer();
    }

    // 3. Envío seguro a servicios dependientes (Transfers & Accounts)
    try {
        disableSubmitButton(); // Evita doble envío en UI
        
        // Log estandarizado (Cumpliendo restricción: sin datos sensibles)
        logger.info(`Iniciando transferencia segura. ID_Destino_Hash: ${hash(transferData.destinationAccount)}`);

        const response = await transfersService.execute({
            from: currentUser.account,
            to: transferData.destinationAccount,
            amount: transferData.amount,
            idempotencyKey: generateIdempotencyKey(transferData) // Mitiga riesgo de duplicados
        });

        if (response.success) {
            return displaySummaryMessage("Transferencia enviada con éxito");
        } else {
            throw new Error(response.errorMessage);
        }

    } catch (error) {
        logger.error(`Error en transferencia: ${error.message}`);
        return displayError("No se pudo completar la transferencia. Intente más tarde.");
    } finally {
        enableSubmitButton();
    }
}
```

## Diagram type
Flujo (Flowchart) combinado con Secuencia básica.

## Target format
PNG

## Technical context
Web Frontend (Componente de confirmación), REST API existente, servicio de Cuentas (`Accounts service`) y servicio de Transferencias (`Transfers service`).

## Key entities/nodes to highlight
- **UI Frontend** (Modal de confirmación y botón de envío).
- **Controlador de Validación** (Validación de montos).
- **Transfers Service** (API REST externa).
- **Idempotency Check** (Punto crítico para mitigar el riesgo de duplicados).

## Flow direction
TB (Arriba-Abajo) para el flujo lógico general de la UI hacia el Backend.