import os
import time
import threading
import multiprocessing
from queue import Queue
from collections import defaultdict

# --- Допоміжні функції ---

def create_test_files(directory="test_docs", num_files=20):
    """Створює тестові файли для перевірки роботи програми."""
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    words = ["apple", "banana", "cherry", "date", "elderberry"]
    file_paths = []
    
    print(f"Генеруємо {num_files} тестових файлів...")
    for i in range(num_files):
        filename = os.path.join(directory, f"file_{i}.txt")
        # Записуємо випадкові слова у файл
        content = " ".join([words[i % len(words)], "some random text", words[(i + 1) % len(words)]])
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        file_paths.append(filename)
        
    return file_paths

def search_keywords_in_files(files, keywords, result_queue=None, result_dict=None):
    """
    Основна логіка пошуку.
    Може записувати результат у Queue (для multiprocessing) 
    або у словник/список (для threading).
    """
    local_results = defaultdict(list)
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                for keyword in keywords:
                    if keyword in content:
                        local_results[keyword].append(file_path)
        except OSError as e:
            print(f"Помилка при читанні файлу {file_path}: {e}")
        except Exception as e:
            print(f"Непередбачена помилка з файлом {file_path}: {e}")

    # Повертаємо результат залежно від механізму
    if result_queue is not None:
        result_queue.put(local_results)
    elif result_dict is not None:
        # Для threading використовуємо Lock, якщо пишемо у спільний ресурс, 
        # але тут ми просто оновимо словник після завершення (або можна повернути local_results)
        # В даному прикладі спростимо: функція повертає local_results
        return local_results
    return local_results

def merge_results(results_list):
    """Об'єднує список словників в один загальний словник."""
    final_dict = defaultdict(list)
    for res in results_list:
        for key, paths in res.items():
            final_dict[key].extend(paths)
    return dict(final_dict)

def chunkify(lst, n):
    """Розділяє список на n приблизно рівних частин."""
    return [lst[i::n] for i in range(n)]

# --- 1. Реалізація threading (Багатопотоковість) ---

def run_threading(files, keywords, num_threads=4):
    start_time = time.time()
    threads = []
    results = []
    
    # Розділяємо файли між потоками
    file_chunks = chunkify(files, num_threads)
    
    # Wrapper для збереження результату потоку (бо Thread не повертає значення напряму)
    def thread_worker(files_chunk, keys, res_list):
        res = search_keywords_in_files(files_chunk, keys)
        res_list.append(res)

    for i in range(num_threads):
        if not file_chunks[i]: # Якщо файлів менше ніж потоків
            continue
        t = threading.Thread(target=thread_worker, args=(file_chunks[i], keywords, results))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    final_result = merge_results(results)
    end_time = time.time()
    
    print(f"Threading time: {end_time - start_time:.4f} seconds")
    return final_result

# --- 2. Реалізація multiprocessing (Багатопроцесорність) ---

def process_worker(files, keywords, queue):
    """Функція-воркер для процесу."""
    search_keywords_in_files(files, keywords, result_queue=queue)

def run_multiprocessing(files, keywords, num_processes=4):
    start_time = time.time()
    processes = []
    queue = multiprocessing.Queue()
    
    # Розділяємо файли між процесами
    file_chunks = chunkify(files, num_processes)

    for i in range(num_processes):
        if not file_chunks[i]:
            continue
        p = multiprocessing.Process(target=process_worker, args=(file_chunks[i], keywords, queue))
        processes.append(p)
        p.start()

    # Збираємо результати з черги
    results_list = []
    for _ in range(len(processes)):
        results_list.append(queue.get())

    for p in processes:
        p.join()

    final_result = merge_results(results_list)
    end_time = time.time()
    
    print(f"Multiprocessing time: {end_time - start_time:.4f} seconds")
    return final_result

# --- Головний блок ---

if __name__ == "__main__":
    # Підготовка даних
    files = create_test_files(num_files=100) # Створимо 100 файлів
    keywords = ["apple", "banana", "unknown_fruit"]

    print("\n--- Запуск Threading ---")
    res_thread = run_threading(files, keywords, num_threads=4)
    # Виведемо приклад результату (кількість знайдених)
    for k, v in res_thread.items():
        print(f"Word '{k}' found in {len(v)} files.")

    print("\n--- Запуск Multiprocessing ---")
    res_process = run_multiprocessing(files, keywords, num_processes=4)
    for k, v in res_process.items():
        print(f"Word '{k}' found in {len(v)} files.")
        
    # Очистка тестових файлів (опціонально)
    # import shutil
    # shutil.rmtree("test_docs")