document.addEventListener('DOMContentLoaded', function() {
    // Manejar añadir al carrito con verificación de login
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function() {
            const productId = this.dataset.productId;
            addToCart(productId, 1);
        });
    });

    // Inicializar funcionalidad del carrito si estamos en la página del carrito
    if (document.querySelector('.cart-container')) {
        initCartFunctionality();
    }
});

function initCartFunctionality() {
    // Variables para el modal
    const modal = document.getElementById('confirmationModal');
    const confirmBtn = document.getElementById('confirmRemove');
    const cancelBtn = document.getElementById('cancelRemove');
    const productNameSpan = document.getElementById('productName');
    let currentProductId = null;
    
    // Agregar event listeners a todos los botones de eliminar
    const removeButtons = document.querySelectorAll('.remove-item');
    removeButtons.forEach(button => {
        button.addEventListener('click', function() {
            currentProductId = this.getAttribute('data-product-id');
            const productName = this.getAttribute('data-product-name');
            
            // Mostrar el nombre del producto en el modal
            if (productNameSpan && productName) {
                productNameSpan.textContent = productName;
            }
            
            // Mostrar el modal de confirmación
            if (modal) {
                modal.style.display = 'flex';
            } else {
                // Si no hay modal, eliminar directamente
                removeItemFromCart(currentProductId);
            }
        });
    });
    
    // Confirmar eliminación
    if (confirmBtn) {
        confirmBtn.addEventListener('click', function() {
            if (currentProductId) {
                removeItemFromCart(currentProductId);
            }
            if (modal) modal.style.display = 'none';
        });
    }
    
    // Cancelar eliminación
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            if (modal) modal.style.display = 'none';
            currentProductId = null;
        });
    }
    
    // Cerrar modal si se hace clic fuera del contenido
    if (modal) {
        window.addEventListener('click', function(event) {
            if (event.target === modal) {
                modal.style.display = 'none';
                currentProductId = null;
            }
        });
    }
    
    // También agregamos funcionalidad a los botones de cantidad
    const quantityButtons = document.querySelectorAll('.quantity-btn');
    quantityButtons.forEach(button => {
        button.addEventListener('click', function() {
            const action = this.getAttribute('data-action');
            const productId = this.getAttribute('data-product-id');
            const quantityElement = this.parentElement.querySelector('.quantity');
            let quantity = parseInt(quantityElement.textContent);
            
            if (action === 'increase') {
                quantity++;
                updateQuantity(productId, quantity, quantityElement);
            } else if (action === 'decrease' && quantity > 1) {
                quantity--;
                updateQuantity(productId, quantity, quantityElement);
            }
        });
    });
}

// Función para eliminar producto del carrito
function removeItemFromCart(productId) {
    console.log('Eliminando producto ID:', productId);
    
    fetch('/remove_from_cart', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            product_id: parseInt(productId)
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Error en la respuesta del servidor');
        }
        return response.json();
    })
    .then(data => {
        console.log('Respuesta del servidor:', data);
        if (data.success) {
            // Encontrar el elemento del carrito y eliminarlo
            const itemToRemove = document.querySelector(`.cart-item[data-product-id="${productId}"]`);
            if (itemToRemove) {
                itemToRemove.remove();
                
                // Actualizar el total
                if (data.total !== undefined) {
                    const totalElement = document.querySelector('.cart-summary h2');
                    if (totalElement) {
                        totalElement.textContent = `Total: $${data.total.toFixed(2)}`;
                    }
                }
                
                // Si no quedan items, mostrar carrito vacío
                const remainingItems = document.querySelectorAll('.cart-item');
                if (remainingItems.length === 0) {
                    const cartItemsContainer = document.querySelector('.cart-items');
                    if (cartItemsContainer) {
                        cartItemsContainer.innerHTML = `
                            <div class="empty-cart">
                                <p>Tu carrito está vacío</p>
                                <a href="/products" class="btn-primary">Seguir comprando</a>
                            </div>
                        `;
                    }
                    
                    const cartSummary = document.querySelector('.cart-summary');
                    if (cartSummary) cartSummary.style.display = 'none';
                }
                
                // Actualizar contador del carrito
                updateCartCount(-1);
                
                // Mostrar mensaje de éxito
                showNotification('Producto eliminado del carrito', 'success');
            }
        } else {
            showNotification('Error: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error al eliminar el producto: ' + error.message, 'error');
    });
}

// Función para actualizar la cantidad
function updateQuantity(productId, quantity, quantityElement) {
    fetch('/update_cart_quantity', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            product_id: parseInt(productId),
            quantity: quantity
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Actualizar la cantidad mostrada
            quantityElement.textContent = quantity;
            
            // Recargar la página para actualizar los totales
            window.location.reload();
        } else {
            showNotification('Error: ' + data.message, 'error');
            // Recargar para restaurar cantidades correctas
            window.location.reload();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error al actualizar la cantidad', 'error');
        window.location.reload();
    });
}

function addToCart(productId, quantity) {
    fetch('/add_to_cart', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            product_id: productId,
            quantity: quantity
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Mostrar mensaje de éxito
            showNotification(data.message, 'success');
            
            // Actualizar contador del carrito si existe
            updateCartCount(1);
            
        } else if (data.redirect) {
            // Redirigir automáticamente a login
            showNotification('Redirigiendo a login...', 'info');
            setTimeout(() => {
                window.location.href = data.redirect;
            }, 1000);
            
        } else {
            // Mostrar otros errores
            showNotification(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error de conexión', 'error');
    });
}

function showNotification(message, type) {
    // Crear notificación
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 5px;
        color: white;
        z-index: 1000;
        font-weight: bold;
    `;
    
    // Estilos según el tipo
    if (type === 'success') {
        notification.style.background = '#4CAF50';
    } else if (type === 'error') {
        notification.style.background = '#f44336';
    } else if (type === 'info') {
        notification.style.background = '#2196F3';
    }
    
    document.body.appendChild(notification);
    
    // Remover después de 3 segundos
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function updateCartCount(change = 0) {
    // Esta función actualiza un contador visual del carrito
    const cartCount = document.getElementById('cart-count');
    if (cartCount) {
        const currentCount = parseInt(cartCount.textContent) || 0;
        const newCount = Math.max(0, currentCount + change);
        cartCount.textContent = newCount;
        
        // Mostrar u ocultar el contador según si hay items
        if (newCount > 0) {
            cartCount.style.display = 'flex';
        } else {
            cartCount.style.display = 'none';
        }
    }
}