import re
import heapq
import nltk
from nltk.corpus import stopwords
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

def extract_keywords(file_path, num_keywords=10):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Remove special characters and digits
    formatted_text = re.sub('[^a-zA-Z]', ' ', text)
    formatted_text = re.sub(r'\s+', ' ', formatted_text)

    # Convert text to lowercase and tokenize
    words = formatted_text.lower().split()

    # Remove stopwords
    stop_words = set(stopwords.words('english'))
    words = [word for word in words if word not in stop_words]

    # Calculate word frequencies and extract top keywords
    word_freq = Counter(words)
    top_keywords = heapq.nlargest(num_keywords, word_freq, key=word_freq.get)

    return top_keywords


# You'll need to install sklearn for this example
# pip install scikit-learn

def cluster_documents(file_paths, num_clusters=5):
    documents = []

    for file_path in file_paths:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            documents.append(text)

    vectorizer = TfidfVectorizer(stop_words="english")
    X = vectorizer.fit_transform(documents)

    kmeans = KMeans(n_clusters=num_clusters)
    kmeans.fit(X)

    return kmeans.labels_
