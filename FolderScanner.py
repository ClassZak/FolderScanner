import os
import ctypes
from colorama import init, Fore

def sanitize_text(text):
    """Удаляет одиночные суррогатные символы из строки"""
    return text.encode('utf-16', 'surrogatepass').decode('utf-16', 'replace')

class Element:
    def __init__(self, path: str) -> None:
        self.path = self.sanitize_path(path)
        self.size = 0

    @staticmethod
    def sanitize_path(path: str) -> str:
        """Очищает путь от некорректных символов"""
        try:
            return sanitize_text(path)
        except Exception as e:
            print(Fore.RED + f"Error sanitizing path {path}: {str(e)}")
            return path

    def human_size(self, size: int) -> str:
        units = ['bytes', 'KB', 'MB', 'GB', 'TB']
        index = 0
        while size >= 1024 and index < 4:
            size /= 1024
            index += 1
        return f'{size:.2f} {units[index]}' if index > 0 else f'{int(size)} bytes'

class Folder(Element):
    def __init__(self, path: str):
        super().__init__(path)
        if not os.path.exists(self.path):
            raise OSError(f'Not found folder with path "{self.path}"')
        if not os.path.isdir(self.path):
            raise OSError(f'Element with path "{self.path}" is not directory')

    def __str__(self):
        return f'Folder\t{self.path}\t{self.human_size(self.size)}'

    def init_elements(self) -> set:
        try:
            elements = set()
            with os.scandir(self.path) as entries:
                for entry in entries:
                    try:
                        full_path = self.sanitize_path(entry.path)
                        if entry.is_file(follow_symlinks=False):
                            elements.add(File(full_path))
                        elif entry.is_dir(follow_symlinks=False):
                            elements.add(Folder(full_path))
                    except (OSError, UnicodeEncodeError) as e:
                        print(Fore.RED + f"Error processing {entry.path}: {str(e)}")
            self.elements = elements
            return elements
        except Exception as e:
            print(Fore.RED + f"Error scanning directory {self.path}: {str(e)}")
            return set()

    def is_special_file(self, path: str) -> bool:
        """Проверяет специальные типы файлов"""
        try:
            if path.lower().endswith('.lnk'):
                return True
            if ctypes.windll.shell32.SHGetFileInfoW(path, 0, None, 0, 0x000000100):
                return True
            return False
        except Exception:
            return False

    def calculate_size(self, min_size=0) -> int:
        total_size = 0
        for el in self.init_elements():
            try:
                if self.is_special_file(el.path):
                    print(Fore.CYAN + f'Skipping special file: {el.path}')
                    continue

                if isinstance(el, Folder):
                    try:
                        el_size = el.calculate_size(min_size)
                    except PermissionError:
                        print(Fore.RED + f'Permission denied: {el.path}')
                        continue
                else:
                    el_size = el.calculate_size()

                if el_size >= min_size:
                    size_info = Fore.YELLOW + f'{el.human_size(el_size)}'
                    print(f'{el.path}\t{size_info}')

                total_size += el_size
                self.size = total_size

            except Exception as e:
                print(Fore.RED + f"Error processing {el.path}: {str(e)}")

        return total_size

    def get_sorted_elements(self) -> list:
        sorted_list = []
        for el in self.elements:
            try:
                if isinstance(el, Folder):
                    sorted_list.extend(el.get_sorted_elements())
                if el.size > 0:
                    sorted_list.append(el)
            except Exception as e:
                print(Fore.RED + f"Error sorting {el.path}: {str(e)}")
        return sorted(sorted_list, key=lambda x: x.size, reverse=True)

class File(Element):
    def __init__(self, path: str):
        super().__init__(path)
        if not os.path.exists(self.path):
            raise OSError(f'Not found file with path "{self.path}"')
        if not os.path.isfile(self.path):
            raise OSError(f'Element with path "{self.path}" is not file')

    def __str__(self):
        return f'File\t{self.path}\t{self.human_size(self.size)}'

    def calculate_size(self) -> int:
        try:
            self.size = os.stat(self.path).st_size
            return self.size
        except Exception as e:
            print(Fore.RED + f"Error getting size for {self.path}: {str(e)}")
            return 0

def saving_dialog(filename: str, elements: list) -> None:
    answer = input(f'Do you want to save results to "{filename}"? [Y/n] -> ').lower()
    if answer in ('y', 'yes', ''):
        try:
            save_sorted_list(filename, elements)
            print(Fore.GREEN + f'Results saved to {filename}')
        except Exception as e:
            print(Fore.RED + f'Error saving file: {str(e)}')
def print_dialog()->bool:
    answer = input(f'Print sorted elements?[Y/n] -> ').lower()
    return answer in ('y', 'yes', '')

def save_sorted_list(filename: str, elements: list) -> None:
    try:
        with open(filename, 'w', encoding='utf-16', errors='replace') as file:
            for el in elements:
                try:
                    file.write(f'{str(el)}\n')
                except UnicodeEncodeError:
                    safe_path = el.path.encode('utf-16', 'replace').decode('utf-16')
                    file.write(f'{el.__class__.__name__}\t{safe_path}\t{el.human_size(el.size)}\n')
    except Exception as e:
        raise RuntimeError(f"Failed to save file: {str(e)}")

def main():
    init(autoreset=True)
    
    while True:
        path = input('Enter path of directory -> ').strip()
        if os.path.exists(path):
            break
        print(Fore.RED + 'Invalid path, please try again')

    while True:
        try:
            min_size = int(input('Enter minimum size for scanning (bytes) -> '))
            if min_size >= 0:
                break
        except:
            print(Fore.RED + 'Please enter a valid non-negative integer')
    
    print_elements=print_dialog()
    
    try:
        f = Folder(os.path.abspath(path))
        total_size = f.calculate_size(min_size)
        print(Fore.YELLOW + '\nTotal size: ' + f'{f.human_size(total_size)}')

        sorted_elements = f.get_sorted_elements()
        if print_elements:
            print("\nSorted results:")
            for el in sorted_elements:
                try:
                    print(f'{el.path} - {Fore.YELLOW}{el.human_size(el.size)}')
                except UnicodeEncodeError:
                    safe_path = el.path.encode('utf-8', 'replace').decode('utf-8')
                    print(f'{safe_path} - {Fore.YELLOW}{el.human_size(el.size)}')

        saving_dialog('results.txt', sorted_elements)
        
    except Exception as e:
        print(Fore.RED + f'Fatal error: {str(e)}')
    finally:
        input('Press Enter to exit...')

if __name__ == '__main__':
    main()