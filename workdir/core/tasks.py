from celery import shared_task
import time

@shared_task
def add(x, y):
    # Using print statements for simple stdout logging from Celery worker
    print(f"Task add: Received request to add {x} + {y}")
    time.sleep(2) # Simulate some work
    result = x + y
    print(f"Task add: Calculation complete. Result is {result}")
    return result

@shared_task
def simple_test_task():
    timestamp = time.time()
    message = f"Simple test task executed successfully at timestamp: {timestamp}"
    print(message)
    # This task could also perform other simple actions,
    # like creating a test file or logging to the database if models were imported.
    return message

@shared_task
def process_imported_page(page_html_content, target_space_key):
    print(f"Task process_imported_page: Received page for space '{target_space_key}'. HTML content length: {len(page_html_content)}")
    # Simulate processing (parsing HTML, converting to ProseMirror JSON, saving models, etc.)
    # In a real scenario, this task would interact with Django models and other services.
    # For example: from pages.models import Page; from workspaces.models import Space;
    time.sleep(3)
    processed_info = f"Successfully processed page (length: {len(page_html_content)}) for space '{target_space_key}'."
    print(f"Task process_imported_page: {processed_info}")
    return processed_info
