/* Resumen del pedido: sincroniza producto, cantidad, precio y dirección.
   Solo actúa si la página tiene el bloque [data-order-summary] (formulario). */
(() => {
    const form = document.querySelector("[data-order-summary]")?.closest("form");

    if (!form) {
        return;
    }

    const product = form.querySelector('select[name="producto"]');
    const quantity = form.querySelector('input[name="cantidad"]');
    const productOutput = form.querySelector("[data-order-product]");
    const quantityOutput = form.querySelector("[data-order-quantity]");
    const totalOutput = form.querySelector("[data-order-total]");
    const unitPriceOutput = form.querySelector("[data-order-unit-price]");
    const addressSection = form.querySelector("[data-delivery-address]");
    const district = form.querySelector('input[name="distrito"]');

    if (!product || !quantity || !productOutput || !quantityOutput || !totalOutput || !unitPriceOutput || !addressSection || !district) {
        return;
    }

    const formatPrice = Miskylac.formatPrice;

    const updateSummary = () => {
        const selectedProduct = product.selectedOptions[0];
        const unitPrice = Number(selectedProduct.dataset.price);
        const quantityValue = Math.max(1, Math.min(99, Number.parseInt(quantity.value, 10) || 1));
        const hasProduct = selectedProduct.value !== "" && Number.isFinite(unitPrice);

        productOutput.textContent = hasProduct ? selectedProduct.value : "Selecciona un producto";
        quantityOutput.textContent = `Cantidad: ${quantityValue}`;
        totalOutput.textContent = formatPrice(hasProduct ? unitPrice * quantityValue : 0);
        unitPriceOutput.textContent = hasProduct
            ? `Precio unitario: ${formatPrice(unitPrice)}. Monto final sujeto a confirmación.`
            : "El monto final se confirma al coordinar el pedido.";
    };

    const updateDeliveryFields = () => {
        const pickup = form.querySelector('input[name="entrega"]:checked')?.value === "recogida";
        addressSection.hidden = pickup;
        addressSection.classList.toggle("hidden", pickup);
        addressSection.querySelectorAll("input").forEach((input) => {
            input.disabled = pickup;
            input.required = !pickup;
            if (pickup) {
                input.value = "";
            }
        });
    };

    product.addEventListener("change", updateSummary);
    quantity.addEventListener("input", updateSummary);
    form.querySelectorAll('input[name="entrega"]').forEach((option) => {
        option.addEventListener("change", updateDeliveryFields);
    });

    updateSummary();
    updateDeliveryFields();
})();
