// Add Book to Liked Books
function renderLikedBooks(data) {
    const likedBooksList = document.getElementById('liked-books');
    likedBooksList.innerHTML = '';
    data.forEach(book => {
        const li = document.createElement('li');
        li.innerHTML = `
            <img src="${book.image_url}" alt="${book.title} cover" width="50">
            <p>${book.title} <span>By: ${book.authors}</span></p>
            <button class="remove-book" onclick="removeBook('${book.title.replace(/'/g, "\\'")}')">X</button>
        `;
        likedBooksList.appendChild(li);
    });
}

// Update the recommendation section of the UI
function updateRecommendationsUI(data) {
    const recommendedBooksList = document.getElementById('recommended-books-list');
    recommendedBooksList.innerHTML = '';

    // If a message is provided, show it and hide the list
    if (data.message) {
        const messageElement = document.getElementById('recommendation-message');
        messageElement.textContent = data.message;
        recommendedBooksList.style.display = 'none';
        return;
    }

    const messageElement = document.getElementById('recommendation-message');
    messageElement.textContent = '';
    recommendedBooksList.style.display = 'grid';

    (data.recommendations || data).forEach(book => {
        const bookItem = document.createElement('div');
        bookItem.className = 'recommended-book-item';
        bookItem.innerHTML = `
            <img src="${book.image_url}" alt="${book.title} cover" />
            <h4>${book.title}</h4>
            <p>By: ${book.authors}</p>
        `;
        recommendedBooksList.appendChild(bookItem);
    });
}

function addBookToLiked(bookTitle = null) {
    if (!bookTitle) {
        bookTitle = document.getElementById('liked-book').value;
    }

    if (bookTitle) {
        fetch('/add_book', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ book: bookTitle })
        })
        .then(response => response.json())
        .then(data => {
            // Clear the input field and dropdown
            document.getElementById('liked-book').value = '';  // Clear input
            document.getElementById('autocomplete-results').innerHTML = '';  // Hide the dropdown
            document.getElementById('autocomplete-results').style.display = 'none';  // Hide dropdown
            
            // Update the liked books list on the UI
            renderLikedBooks(data.liked_books);

            // Update recommendations based on server response
            updateRecommendationsUI(data);
        })
        .catch(error => {
            console.error('Error:', error);
        });
    } else {
        alert("Please enter a book name.");
    }
}

// Function to handle Enter key press in the input
document.getElementById('liked-book').addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
        event.preventDefault();  // Prevent form submission or default behavior
        addBookToLiked();
    }
});

// Load liked books when the page is first opened
document.addEventListener('DOMContentLoaded', function() {
    fetch('/liked_books')
        .then(response => response.json())
        .then(data => {
            if (Array.isArray(data)) {
                renderLikedBooks(data);
                if (data.length > 0) {
                    getRecommendations();
                }
            }
        })
        .catch(error => {
            console.error('Error fetching liked books:', error);
        });
});


function removeBook(bookTitle) {
    fetch('/remove_book', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ book_title: bookTitle })
    })
    .then(response => response.json())
    .then(data => {
        // Clear and update the liked books list after removal
        renderLikedBooks(data);

        // Get and display recommendations after removing a book
        getRecommendations();
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function getRecommendations() {
    fetch('/get_recommendations')
        .then(response => response.json())
        .then(data => {
            updateRecommendationsUI(data);
        })
        .catch(error => {
            console.error('Error fetching recommendations:', error);
        });
}


// Function to search books and show dropdown
function searchBooks(event) {
    const searchQuery = event.target.value;
    if (searchQuery.length > 0) {
        fetch(`/search_books?query=${encodeURIComponent(searchQuery)}`)
        .then(response => response.json())
        .then(data => {
            const autocompleteResults = document.getElementById('autocomplete-results');
            autocompleteResults.innerHTML = '';  // Clear any previous results

            // Check if 'items' is present and is an array
            if (data.items && Array.isArray(data.items)) {
                data.items.forEach(book => {
                    // Extract details returned by our Flask endpoint
                    const title = book.title || 'No Title';
                    const authors = book.authors || 'Unknown Author';
                    const imageUrl = book.image_url || '';
                    
                    // Create the dropdown item with title, author, and cover image
                    const li = document.createElement('li');
                    li.innerHTML = `
                        <div style="display: flex; align-items: center;">
                            <img src="${imageUrl}" alt="${title} cover" width="30" style="margin-right: 10px;">
                            <div>
                                <strong>${title}</strong>
                                <p style="font-size: 0.8em; color: #555;">By: ${authors}</p>
                            </div>
                        </div>
                    `;
                    li.onclick = function() {
                        addBookToLiked(title);  // Add book when clicked
                        document.getElementById('autocomplete-results').style.display = 'none';  // Hide dropdown
                    };
                    autocompleteResults.appendChild(li);
                });

                // Show dropdown
                autocompleteResults.style.display = 'block';
            } else {
                // Handle if the API response does not contain 'items' array or if it's empty
                console.error("API response does not contain 'items' array:", data);
                autocompleteResults.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error fetching books:', error);
        });
    } else {
        document.getElementById('autocomplete-results').style.display = 'none'; // Hide dropdown if no input
    }
}
