(function () {
    const body = document.body;
    if (!body.dataset.cartEndpoint) {
        return;
    }

    const endpoint = body.dataset.cartEndpoint;
    const productsUrl = body.dataset.productsUrl || '/shop/products/';

    function getCookie(name) {
        const cookies = document.cookie ? document.cookie.split('; ') : [];
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i];
            if (cookie.startsWith(name + '=')) {
                return decodeURIComponent(cookie.split('=').slice(1).join('='));
            }
        }
        return null;
    }

    function showNotification(message, level = 'info') {
        let container = document.querySelector('.js-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'js-toast-container position-fixed pos-top pos-right p-3';
            container.style.zIndex = '9999';
            body.appendChild(container);
        }

        const alert = document.createElement('div');
        alert.className = `alert alert-${level} fade show mb-2 shadow`;
        alert.role = 'alert';
        alert.textContent = message;
        container.appendChild(alert);

        setTimeout(() => {
            alert.classList.remove('show');
            alert.addEventListener('transitionend', () => alert.remove());
        }, 2200);
    }

    async function postCart(payload) {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') || '',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            throw new Error('No fue posible actualizar el carrito.');
        }

        return response.json();
    }

    function refreshBadge(count) {
        const badge = document.querySelector('.js-cart-count');
        if (badge) {
            badge.textContent = count;
            badge.classList.toggle('d-none', count === 0);
        }
        const text = document.querySelector('.js-cart-count-text');
        if (text) {
            text.textContent = count;
        }
    }

    function refreshCartTable(snapshot) {
        snapshot.items.forEach((item) => {
            const row = document.querySelector(`.js-cart-row[data-product="${item.id}"]`);
            if (row) {
                if (item.quantity > 0) {
                    const qtyNode = row.querySelector('.js-cart-quantity');
                    const subtotalNode = row.querySelector('.js-cart-subtotal');
                    if (qtyNode) {
                        qtyNode.textContent = item.quantity;
                    }
                    if (subtotalNode) {
                        const currency = subtotalNode.dataset.currency || '$';
                        subtotalNode.dataset.value = item.subtotal;
                        subtotalNode.textContent = `${currency}${parseFloat(item.subtotal).toFixed(2)}`;
                    }
                } else {
                    row.remove();
                }
            }
        });

        const existingRows = document.querySelectorAll('.js-cart-row');
        existingRows.forEach((row) => {
            const productId = parseInt(row.dataset.product, 10);
            const stillInCart = snapshot.items.some((item) => item.id === productId);
            if (!stillInCart) {
                row.remove();
            }
        });

        const summary = document.querySelector('[data-cart-summary]');
        if (summary) {
            const totalNode = summary.querySelector('.js-cart-total');
            if (totalNode) {
                const currency = totalNode.dataset.currency || '$';
                totalNode.dataset.total = snapshot.total;
                totalNode.textContent = `${currency}${parseFloat(snapshot.total).toFixed(2)}`;
            }
        }

        if (!document.querySelector('.js-cart-row')) {
            const cardBody = document.querySelector('.card-body');
            if (cardBody) {
            cardBody.innerHTML = `
                    <div class="text-center py-5">
                        <p class="lead text-muted mb-4">Tu carrito está vacío.</p>
                        <a href="${productsUrl}" class="btn btn-primary">
                            <i class="fal fa-store"></i> Ver productos
                        </a>
                    </div>
                `;
            }
        }
    }

    function getQuantityFromControl(control) {
        const wrapper = control.closest('.input-group');
        if (!wrapper) return 1;
        const input = wrapper.querySelector('.js-qty-input');
        return input ? parseInt(input.value, 10) || 1 : 1;
    }

    function updateQuantityControl(button) {
        const wrapper = button.closest('.input-group');
        if (!wrapper) return;
        const input = wrapper.querySelector('.js-qty-input');
        if (!input) return;
        const current = parseInt(input.value, 10) || 1;
        if (button.dataset.action === 'increment') {
            input.value = current + 1;
        } else if (button.dataset.action === 'decrement') {
            input.value = Math.max(1, current - 1);
        }
    }

    function attachQuantityListeners() {
        document.querySelectorAll('.js-qty-btn').forEach((button) => {
            button.addEventListener('click', (event) => {
                event.preventDefault();
                updateQuantityControl(button);
            });
        });
    }

    async function handleCartAction(productId, action, quantity) {
        try {
            const payload = {
                productId,
                action,
                quantity: parseInt(quantity, 10) || 1,
            };
            const snapshot = await postCart(payload);
            refreshBadge(snapshot.count);
            refreshCartTable(snapshot);
            showNotification(snapshot.message || 'Carrito actualizado.');
        } catch (error) {
            console.error(error);
            showNotification(error.message, 'danger');
        }
    }

    function attachCartButtons() {
        document.querySelectorAll('.js-add-to-cart').forEach((button) => {
            button.addEventListener('click', (event) => {
                event.preventDefault();
                const productId = button.dataset.product;
                const quantity = getQuantityFromControl(button);
                handleCartAction(productId, 'add', quantity);
            });
        });

        document.querySelectorAll('.js-update-cart').forEach((button) => {
            button.addEventListener('click', (event) => {
                event.preventDefault();
                const productId = button.dataset.product;
                const action = button.dataset.action;
                handleCartAction(productId, action, 1);
            });
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        attachQuantityListeners();
        attachCartButtons();
    });
})();
