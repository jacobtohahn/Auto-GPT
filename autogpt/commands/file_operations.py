"""File operations for AutoGPT"""
from __future__ import annotations

import os
import os.path
from pathlib import Path
from typing import Generator, List, Union
import requests
from requests.adapters import HTTPAdapter, Retry
from colorama import Fore, Back
from autogpt.spinner import Spinner
from autogpt.utils import readable_file_size
from autogpt.workspace import path_in_workspace, WORKSPACE_PATH
import shutil
import fnmatch

from autogpt.smart_utils import summarize_contents

from pdfminer.high_level import extract_text

# Create the directory if it doesn't exist
if not os.path.exists(WORKSPACE_PATH):
    os.makedirs(WORKSPACE_PATH)


LOG_FILE = "file_logger.txt"
LOG_FILE_PATH = WORKSPACE_PATH / LOG_FILE


def check_duplicate_operation(operation: str, filename: str) -> bool:
    """Check if the operation has already been performed on the given file

    Args:
        operation (str): The operation to check for
        filename (str): The name of the file to check for

    Returns:
        bool: True if the operation has already been performed on the file
    """
    log_content = read_file(LOG_FILE)
    log_entry = f"{operation}: {filename}\n"
    return log_entry in log_content


def log_operation(operation: str, filename: str, filename2: str = None) -> None:
    """Log the file operation to the file_logger.txt

    Args:
        operation (str): The operation to log
        filename (str): The name of the file the operation was performed on
    """

    if filename2:
        log_entry = f"{operation}: {filename} to {filename2}\n"
    else:
        log_entry = f"{operation}: {filename}\n"

    # Create the log file if it doesn't exist
    if not os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write("File Operation Logger ")

    append_to_file(LOG_FILE, log_entry, shouldLog = False)


# Ensure lower_snake_case filenames
def format_filename(filename):
    """Format a filename to be lowercase with underscores"""
    # Split the file path into directory and file name components
    directory, file_name = os.path.split(filename)
    
    # Replace any spaces in the file name with underscores
    file_name = file_name.replace(' ', '_')
    
    # Convert the file name to lowercase
    file_name = file_name.lower()
    
    # Rejoin the directory and file name components to create the full path
    formatted_filename = os.path.join(directory, file_name)
    
    return formatted_filename


def split_file(
    content: str, max_length: int = 4000, overlap: int = 0
) -> Generator[str, None, None]:
    """
    Split text into chunks of a specified maximum length with a specified overlap
    between chunks.

    :param content: The input text to be split into chunks
    :param max_length: The maximum length of each chunk,
        default is 4000 (about 1k token)
    :param overlap: The number of overlapping characters between chunks,
        default is no overlap
    :return: A generator yielding chunks of text
    """
    start = 0
    content_length = len(content)

    while start < content_length:
        end = start + max_length
        if end + overlap < content_length:
            chunk = content[start : end + overlap]
        else:
            chunk = content[start:content_length]
        yield chunk
        start += max_length - overlap


def read_file(filename: str) -> str:
    """Read a file and return the contents

    Args:
        filename (str): The name of the file to read

    Returns:
        str: The contents of the file
    """
    try:
        filepath = path_in_workspace(filename)

        # Check if the file is a PDF and extract text if so
        if is_pdf(filepath):
            text = extract_text(filepath)
            
            if not text:
                return "Error: Could not extract text from PDF"
            else:
                return text
        else:
            with open(filepath, "r", encoding='utf-8') as f:
                content = f.read()
            return content
    except Exception as e:
        return handle_file_error("read", filename, str(e))


def ingest_file(
    filename: str, memory, max_length: int = 4000, overlap: int = 200
) -> None:
    """
    Ingest a file by reading its content, splitting it into chunks with a specified
    maximum length and overlap, and adding the chunks to the memory storage.

    :param filename: The name of the file to ingest
    :param memory: An object with an add() method to store the chunks in memory
    :param max_length: The maximum length of each chunk, default is 4000
    :param overlap: The number of overlapping characters between chunks, default is 200
    """
    try:
        print(f"Working with file {filename}")
        content = read_file(filename)
        content_length = len(content)
        print(f"File length: {content_length} characters")

        chunks = list(split_file(content, max_length=max_length, overlap=overlap))

        num_chunks = len(chunks)
        for i, chunk in enumerate(chunks):
            print(f"Ingesting chunk {i + 1} / {num_chunks} into memory")
            memory_to_add = (
                f"Filename: {filename}\n" f"Content part#{i + 1}/{num_chunks}: {chunk}"
            )

            memory.add(memory_to_add)

        print(f"Done ingesting {num_chunks} chunks from {filename}.")
    except Exception as e:
        print(f"Error while ingesting file '{filename}': {str(e)}")


# Add find_file as a command in the future
def find_file(filename: str, path: str = WORKSPACE_PATH) -> str:
    """Recursively search for a file with the given filename in the filesystem.

    Args:
        filename (str): The name of the file to search for.
        path (str, optional): The path to start the search from. Defaults to WORKSPACE_PATH.

    Returns:
        str: The path to the found file or an empty string if the file is not found.
    """
    for root, dirs, files in os.walk(path):
        if filename in files:
            return os.path.join(root, filename)

    return ""


def find_files(pattern: str, path: str = WORKSPACE_PATH) -> List[str]:
    matched_files = []
    for root, _, files in os.walk(path):
        for filename in files:
            if fnmatch.fnmatch(filename, pattern):
                matched_files.append(os.path.join(root, filename))
    return matched_files


def write_to_file(filename: str, text: str) -> str:
    """Write text to a file

    Args:
        filename (str): The name of the file to write to
        text (str): The text to write to the file

    Returns:
        str: A message indicating success or failure
    """
    if check_duplicate_operation("write", filename):
        return "Error: File has already been updated."
    try:
        formatted_filename = format_filename(filename)
        filepath = path_in_workspace(formatted_filename)
        existing_filepath = find_file(formatted_filename)

        if existing_filepath and (filepath != path_in_workspace(existing_filepath)):
            print(filepath)
            return f"A file with that name already exists in a different location: {existing_filepath}. Use append_to_file instead."
        else:
            directory = os.path.dirname(filepath)
            if not os.path.exists(directory):
                os.makedirs(directory)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        log_operation("write", filepath)
        return f"File {filename} written to successfully. Your current files are now: {list_resources()}"
    except Exception as e:
        return handle_file_error("write", filename, str(e))


def append_to_file(filename: str, text: str, shouldLog: bool = True) -> str:
    """Append text to a file

    Args:
        filename (str): The name of the file to append to
        text (str): The text to append to the file

    Returns:
        str: A message indicating success or failure
    """
    try:
        formatted_filename = format_filename(filename)
        filepath = path_in_workspace(formatted_filename)
        existing_filepath = find_file(formatted_filename)

        if existing_filepath and (filepath != path_in_workspace(existing_filepath)):
            return f"A file with that name already exists in a different location: {existing_filepath}"
        else:
            directory = os.path.dirname(filepath)
            if not os.path.exists(directory):
                os.makedirs(directory)

        with open(filepath, "a") as f:
            f.write(text)

        if shouldLog and (filename != "file_logger.txt"):
            log_operation("append", filepath)

        return f"Text appended to {filename} successfully. Your current files are now: {list_resources()}"
    except Exception as e:
        return handle_file_error("append", filename, str(e))


def delete_file(filename: Union[str, List]) -> str:
    try:
        if isinstance(filename, str):
            filename = [filename]
        files_deleted = []
        errors = []
        for file in filename:
            if check_duplicate_operation("delete", file):
                errors.append(f"Error: File {file} has already been deleted.")
                continue
            formatted_filename = format_filename(file)
            found_filepaths = find_files(formatted_filename)
            if not found_filepaths:
                errors.append(f"Error: File {file} not found.")
                continue
            for found_filepath in found_filepaths:
                os.remove(found_filepath)
                log_operation("delete", found_filepath)
                files_deleted.append(os.path.basename(found_filepath))

        response = f"Files {files_deleted} deleted successfully. Your current files are now: {list_resources()}"
        if errors:
            response += f"\nErrors encountered:\n" + "\n".join(errors)
        return response
    except Exception as e:
        return handle_file_error("delete", filename, str(e))

def copy_file(src_filename: Union[str, List], dest_directory: str):
    try:
        if isinstance(src_filename, str):
            src_filename = [src_filename]
        files_copied = []
        errors = []
        for file in src_filename:
            formatted_src_filename = format_filename(file)
            found_filepaths = find_files(formatted_src_filename)
            if not found_filepaths:
                errors.append(f"Error: File {file} not found.")
                continue
            dest_directory_path = os.path.join(WORKSPACE_PATH, path_in_workspace(dest_directory))
            if not os.path.exists(dest_directory_path):
                os.makedirs(dest_directory_path)
            for found_filepath in found_filepaths:
                dest_filepath = os.path.join(dest_directory_path, os.path.basename(found_filepath))
                shutil.copy2(found_filepath, dest_filepath)
                log_operation("copy", found_filepath, dest_filepath)
                files_copied.append(os.path.basename(found_filepath))

        response = f"Files {files_copied} copied successfully. Your current files are now: {list_resources()}"
        if errors:
            response += f"\nErrors encountered:\n" + "\n".join(errors)
        return response
    except Exception as e:
        return handle_file_error("copy", src_filename, str(e))
    
def move_file(src_filename: Union[str, List], dest_directory: str):
    try:
        if isinstance(src_filename, str):
            src_filename = [src_filename]
        files_moved = []
        errors = []
        for file in src_filename:
            formatted_src_filename = format_filename(file)
            found_filepaths = find_files(formatted_src_filename)
            if not found_filepaths:
                errors.append(f"Error: File {file} not found.")
                continue
            dest_directory_path = os.path.join(WORKSPACE_PATH, path_in_workspace(dest_directory))
            if not os.path.exists(dest_directory_path):
                os.makedirs(dest_directory_path)
            for found_filepath in found_filepaths:
                dest_filepath = os.path.join(dest_directory_path, os.path.basename(found_filepath))
                os.rename(found_filepath, dest_filepath)
                log_operation("move", found_filepath, dest_filepath)
                files_moved.append(os.path.basename(found_filepath))

        response = f"Files {files_moved} moved successfully. Your current files are now: {list_resources()}"
        if errors:
            response += f"\nErrors encountered:\n" + "\n".join(errors)
        return response
    except Exception as e:
        return handle_file_error("move", src_filename, str(e))

def rename_file(old_filenames: Union[str, List], new_filenames: Union[str, List]) -> str:
    try:
        if isinstance(old_filenames, str):
            old_filenames = [old_filenames]
        if isinstance(new_filenames, str):
            new_filenames = [new_filenames]

        if len(old_filenames) != len(new_filenames):
            return "Error: The number of old filenames and new filenames must be the same."

        files_renamed = []
        errors = []

        for old_filename, new_filename in zip(old_filenames, new_filenames):
            old_formatted_filename = format_filename(old_filename)
            new_formatted_filename = format_filename(new_filename)
            found_filepaths = find_files(old_formatted_filename)
            if not found_filepaths:
                errors.append(f"Error: File {old_filename} not found.")
                continue

            for found_filepath in found_filepaths:
                new_filepath = os.path.join(os.path.dirname(found_filepath), new_formatted_filename)
                os.rename(found_filepath, new_filepath)
                log_operation("rename", found_filepath, new_filepath)
                files_renamed.append((old_filename, new_filename))

        response = f"Files {files_renamed} renamed successfully. Your current files are now: {list_resources()}"
        if errors:
            response += f"\nErrors encountered:\n" + "\n".join(errors)
        return response
    except Exception as e:
        return handle_file_error("rename", old_filenames, str(e))

def search_files(directory: str, search_phrase: str) -> list[str]:
    try:
        """Search for files in a directory containing the search_phrase

        Args:
            directory (str): The directory to search in
            search_phrase (str): The search phrase or wildcard pattern to match

        Returns:
            list[str]: A list of files found in the directory containing the search phrase
        """

        if directory in {"", "/", ".", "./"}:
            search_directory = WORKSPACE_PATH
        else:
            search_directory = path_in_workspace(directory)

        if not os.path.isdir(search_directory):
            return "Error: directory does not exist"

        found_files = find_files(search_directory)

        return found_files
    except Exception as e:
        return handle_file_error("search", directory, str(e))


def create_directory(directory: Union[str, List]):
    try:
        if isinstance(directory, str):
            directory = [directory]
        directories_created = []
        for dir in directory:
            dir = format_filename(dir)
            dir_path = path_in_workspace(dir)
            os.makedirs(dir_path, exist_ok=True)
            directories_created.append(os.path.basename(dir))
        return f"Directories '{directories_created}' created successfully. Your current files are now: {list_resources()}"
    except Exception as e:
        return handle_file_error("create", directory, str(e))
    
def remove_directory(directory: Union[str, List]):
    try:
        if isinstance(directory, str):
            directory = [directory]
        directories_removed = []
        errors = []
        for dir in directory:
            dir = format_filename(dir)
            dir_path = path_in_workspace(dir)
            if not os.path.isdir(dir_path):
                errors.append(dir)
            os.removedirs(dir_path)
            directories_removed.append(os.path.basename(dir))
        response = f"Directories '{directories_removed}' removed successfully. Your current files are now: {list_resources()}"
        if errors:
            response += f"\nErrors encountered:\n" + "\n".join(errors)
        return response
    except Exception as e:
        return handle_file_error("remove", directory, str(e))

def move_directory(src_directory: Union[str, List], dest_directory: str):
    try:
        if isinstance(src_directory, str):
            src_directory = [src_directory]

            dirs_moved = []
            errors = []

            for dir in src_directory:
                dir = format_filename(dir)
                src_path = path_in_workspace(dir)
                dest_path = path_in_workspace(dest_directory)
                if not os.path.isdir(src_path):
                    errors.append(dir)
                shutil.move(src_path, dest_path)
                dirs_moved.append(os.path.basename(dir))
            response = f"Directories '{dirs_moved}' moved successfully. Your current files are now: {list_resources()}"
            if errors:
                response += f"\nErrors encountered:\n" + "\n".join(errors)
            return response
    except Exception as e:
        return handle_file_error("move", src_directory, str(e))

def list_resources(directory=None):
    if directory is None:
        directory = WORKSPACE_PATH
        
    resource_list = []

    for entry in os.scandir(directory):
        if not entry.name.startswith('.'):
            if entry.is_dir():
                resource_list.append(f"Folder: {entry.name}")
                resource_list += list_resources(os.path.join(directory, entry.name))
            elif entry.is_file():
                resource_list.append(f"File: {entry.name}")

    return resource_list

def resources_to_string(resource_list):
    resources_string = "Resource file map:\n"
    for resource in resource_list:
        resources_string += f"{resource}\n"

    return resources_string

def summarize_resources():
    return f"Summary of contents:\n{summarize_contents(WORKSPACE_PATH)}\n\nResource file map:\n{(list_resources())}"

def get_directory_summary(directory):
    summary = []
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, 'r') as f:
                content = f.read()
            summary.append({'file_path': file_path, 'content': content})
    return summary

def is_pdf(file_path):
    with open(file_path, 'rb') as file:
        file_header = file.read(5)
    return file_header == b'%PDF-'

def get_filesystem_representation(path: str = WORKSPACE_PATH, level: int = 0) -> str:
    """
    Generate a human-readable one-line JSON-like representation of a filesystem, starting from the given path.

    Args:
        path (str, optional): The starting path of the filesystem representation.
        Defaults to WORKSPACE_PATH.
        level (int, optional): The current level of indentation. Defaults to 0.

    Returns:
        str: The filesystem representation as a formatted string.
    """
    if not os.path.exists(path):
        return ""

    representation = ""
    entries = sorted(os.listdir(path))
    file_prefix = "file: "
    dir_prefix = "dir: "

    for entry in entries:
        entry_path = os.path.join(path, entry)
        if os.path.isfile(entry_path):
            representation += file_prefix + entry.replace(' ', '_') + ", "
        elif os.path.isdir(entry_path):
            if len(entries) > 0:
                representation += dir_prefix + entry.replace(' ', '_') + " {"
                representation += get_filesystem_representation(entry_path, level + 1)
                representation += "}, "

    return representation.strip().rstrip(',')


def handle_file_error(operation: str, filename: str, error: str) -> str:
    """
    Handle file-related errors by printing a message with the current filesystem and the error.

    Args:
        operation (str): The operation being performed on the file.
        filename (str): The filename involved in the error.
        error (str): The error message.

    Returns:
        str: The full error message containing the operation, filename, error, and current filesystem.
    """
    current_filesystem = get_filesystem_representation(WORKSPACE_PATH)
    error_message = f"Error trying to {operation} {filename} - File likely doesn't exist. Current filesystem:\n{current_filesystem}\nError: {error}"
    print(error_message)
    return error_message


def download_file(url, filename):
    """Downloads a file
    Args:
        url (str): URL of the file to download
        filename (str): Filename to save the file as
    """
    safe_filename = path_in_workspace(filename)
    try:
        message = f"{Fore.YELLOW}Downloading file from {Back.LIGHTBLUE_EX}{url}{Back.RESET}{Fore.RESET}"
        with Spinner(message) as spinner:
            session = requests.Session()
            retry = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('http://', adapter)
            session.mount('https://', adapter)

            total_size = 0
            downloaded_size = 0

            with session.get(url, allow_redirects=True, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('Content-Length', 0))
                downloaded_size = 0

                with open(safe_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded_size += len(chunk)

                         # Update the progress message
                        progress = f"{readable_file_size(downloaded_size)} / {readable_file_size(total_size)}"
                        spinner.update_message(f"{message} {progress}")

            return f'Successfully downloaded and locally stored file: "{filename}"! (Size: {readable_file_size(total_size)})'
    except requests.HTTPError as e:
        return f"Got an HTTP Error whilst trying to download file: {e}"
    except Exception as e:
        return "Error: " + str(e)
