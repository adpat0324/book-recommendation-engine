import requests
import gensim.downloader as api
import numpy as np
from flask import Flask, render_template, request, jsonify
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

# Load pre-trained GloVe model (300-dimensional vectors)
glove_model = api.load("glove-wiki-gigaword-300")

# In-memory list of books liked by the user (stores title, author, genre, description, and image)
liked_books = []

# Function to query the Google Books API for book details
def get_book_info(book_name):
    url = f'https://www.googleapis.com/books/v1/volumes?q={book_name}'
    response = requests.get(url)
    data = response.json()

    if 'items' not in data:
        return None  # No books found
    
    book_data = data['items'][0]['volumeInfo']
    title = book_data.get('title', 'No Title Found')
    authors = book_data.get('authors', ['Unknown Author'])
    description = book_data.get('description', 'No description available.')
    image_url = book_data.get('imageLinks', {}).get('thumbnail', '')
    
    genre = ', '.join(book_data.get('categories', [])) if 'categories' in book_data else 'Unknown Genre'

    return {
        'title': title,
        'authors': ', '.join(authors),
        'description': description,  # Description is used for similarity
        'genre': genre,
        'image_url': image_url
    }

# Function to get vector representation for a description using GloVe
def get_glove_vector(description):
    words = description.split()
def get_glove_vector(text):
    words = text.split()
    vector = np.zeros(300)  # GloVe vectors are 300-dimensional
    word_count = 0
    for word in words:
        if word in glove_model:
            vector += glove_model[word]
            word_count += 1
    return vector / word_count if word_count > 0 else vector

# Create a combined vector for a book using title, authors, description, and genre
def create_book_vector(book):
    description_vec = get_glove_vector(book.get('description', ''))
    title_vec = get_glove_vector(book.get('title', ''))
    authors_vec = get_glove_vector(book.get('authors', ''))
    genre_vec = get_glove_vector(book.get('genre', ''))

    # Weighted combination: description has highest weight
    combined = (0.6 * description_vec +
                0.2 * title_vec +
                0.1 * authors_vec +
                0.1 * genre_vec)

    return combined

# Function to calculate cosine similarity between two vectors
def cosine_similarity_vectors(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

# Function to get similar books from a large dataset (Google Books API)
def recommend_books(liked_books):
    if len(liked_books) < 1:
        return []

    # Combine descriptions, genres, authors for similarity calculation
    combined_descriptions = " ".join([book['description'] for book in liked_books])
    search_query = combined_descriptions[:50]  # Get first 50 characters as a search query to find similar books
    # Build a search query using titles, authors and genres of liked books
    search_elements = []
    for book in liked_books:
        search_elements.append(book.get('title', ''))
        search_elements.append(book.get('authors', ''))
        if book.get('genre') and book['genre'] != 'Unknown Genre':
            search_elements.append(book['genre'])
    combined_search = " ".join(search_elements)
    search_query = combined_search[:80]  # limit query length for API call

    # Call Google Books API to get books based on a search query
    url = f'https://www.googleapis.com/books/v1/volumes?q={search_query}'
    response = requests.get(url)
    books_data = response.json().get('items', [])
    
    # Get descriptions and vectors for the books fetched from Google Books API
    # Collect book information from the API
    fetched_books = []
    for book in books_data:
        book_info = book['volumeInfo']
        description = book_info.get('description', '')
        title = book_info.get('title', '')
        authors = book_info.get('authors', ['Unknown Author'])
        genre = ', '.join(book_info.get('categories', [])) if 'categories' in book_info else 'Unknown Genre'
        image_url = book_info.get('imageLinks', {}).get('thumbnail', '')
        

        # Create a dictionary of book information
        fetched_books.append({
            'title': title,
            'authors': ', '.join(authors),
            'description': description,
            'genre': genre,
            'image_url': image_url
        })
    
    # Compare each fetched book with the liked books using GloVe embeddings
    liked_vectors = np.array([get_glove_vector(book['description']) for book in liked_books])
    # Compare each fetched book with the liked books using aggregated vectors
    liked_vectors = np.array([create_book_vector(book) for book in liked_books])
    recommended_books = []
    
    for fetched_book in fetched_books:
        fetched_vector = get_glove_vector(fetched_book['description'])
        fetched_vector = create_book_vector(fetched_book)
        similarities = []
        
        for liked_vector in liked_vectors:
            similarity = cosine_similarity_vectors(liked_vector, fetched_vector)
            similarities.append(similarity)
        
        avg_similarity = np.mean(similarities)
        if avg_similarity > 0.1:  # We recommend books with a similarity above a threshold
            recommended_books.append(fetched_book)
    
    return recommended_books[:5]  # Return top 5 recommended books

# Route to get book recommendations
@app.route('/get_recommendations', methods=['GET'])
def get_recommendations():
    if len(liked_books) < 3:
        return jsonify({"message": "Add at least 3 books to get recommendations."})

    recommended_books = recommend_books(liked_books)

    if not recommended_books:
        return jsonify({"message": "No recommendations available at the moment."})

    return jsonify(recommended_books)

# Route to search for books
@app.route('/search_books')
def search_books():
    query = request.args.get('query')
    url = f'https://www.googleapis.com/books/v1/volumes?q={query}'
    response = requests.get(url)
    data = response.json()
    
    books = []
    if 'items' in data:
        for item in data['items']:
            book_info = item.get('volumeInfo', {})
            books.append({
                'title': book_info.get('title', 'No Title'),
                'authors': ', '.join(book_info.get('authors', ['Unknown Author'])),
                'image_url': book_info.get('imageLinks', {}).get('thumbnail', ''),
                'description': book_info.get('description', '')
            })
    
    return jsonify({'items': books})

@app.route('/')
def index():
    return render_template('index.html', liked_books=liked_books)

@app.route('/add_book', methods=['POST'])
def add_book():
    book_name = request.json.get('book')

    if book_name:
        book_info = get_book_info(book_name)

        if book_info:
            liked_books.append(book_info)

    # Prepare recommendations dynamically based on updated list
    message = ""
    recommended_books = []

    if len(liked_books) < 3:
        message = "Add at least 3 books to get recommendations."
    else:
        recommended_books = recommend_books(liked_books)
        if not recommended_books:
            message = "No recommendations available at the moment."

    return jsonify({
        'liked_books': liked_books,
        'recommendations': recommended_books,
        'message': message
    })

@app.route('/remove_book', methods=['POST'])
def remove_book():
    book_title = request.json.get('book_title')

    global liked_books
    liked_books = [book for book in liked_books if book['title'] != book_title]

    return jsonify(liked_books)

# Route to retrieve currently liked books
@app.route('/liked_books', methods=['GET'])
def get_liked_books():
    """Return the list of liked books as JSON."""
    return jsonify(liked_books)

if __name__ == '__main__':
    app.run(debug=True)

