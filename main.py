import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import init, Fore, Style
import time
import re

# Khởi tạo colorama cho Windows
init(autoreset=True)

class FacebookUIDChecker:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        })
        self.live_count = 0
        self.die_count = 0
        self.results = []
    
    def check_uid_picture(self, uid):
        """Kiểm tra UID bằng cách kiểm tra redirect của picture API"""
        try:
            # Thử nhiều lần như C# code
            for attempt in range(3):
                try:
                    url = f"https://graph.facebook.com/{uid}/picture?type=normal"
                    response = self.session.get(url, allow_redirects=True, timeout=10)
                    
                    # Lấy URL cuối cùng sau khi redirect
                    final_url = response.url
                    
                    # Kiểm tra host
                    if "static.xx.fbcdn.net" in final_url or "static.xx.fbcdn" in final_url:
                        # Ảnh mặc định -> DIE
                        return False, "Tài khoản không tồn tại hoặc bị khóa"
                    elif "scontent" in final_url:
                        # Ảnh thật -> LIVE
                        return True, None
                    else:
                        # Các trường hợp khác coi như LIVE
                        return True, None
                        
                except requests.exceptions.Timeout:
                    if attempt < 2:
                        time.sleep(0.5)
                        continue
                    return False, "Timeout"
                    
            return False, "Không thể kiểm tra"
            
        except Exception as e:
            return False, f"Lỗi: {str(e)}"
    
    def get_name_from_profile(self, uid):
        """Lấy tên từ profile page"""
        try:
            url = f"https://www.facebook.com/{uid}"
            response = self.session.get(url, timeout=10)
            
            # Thử lấy tên từ title tag
            title_match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1)
                # Loại bỏ " | Facebook", " - Facebook", "(Sun)" etc
                name = re.sub(r'\s*[\|\-]\s*Facebook.*$', '', title).strip()
                name = re.sub(r'\([^\)]+\)\s*$', '', name).strip()
                if name and 'Facebook' != name and 'Log into' not in name and 'Đăng nhập' not in name:
                    return name
            
            # Thử lấy từ meta tag
            meta_match = re.search(r'<meta property="og:title" content="([^"]+)"', response.text)
            if meta_match:
                name = meta_match.group(1).strip()
                name = re.sub(r'\([^\)]+\)\s*$', '', name).strip()
                if name:
                    return name
                    
            return "Không lấy được tên"
            
        except:
            return "Không lấy được tên"
    
    def check_uid(self, uid):
        """Kiểm tra một UID Facebook"""
        try:
            # Kiểm tra bằng picture method (nhanh và chính xác)
            is_live, error = self.check_uid_picture(uid)
            
            if is_live:
                # Nếu LIVE, thử lấy tên
                name = self.get_name_from_profile(uid)
                
                result = {
                    'uid': uid,
                    'status': 'LIVE',
                    'name': name,
                    'url': f'https://www.facebook.com/{uid}',
                    'error': None
                }
                print(f"{Fore.GREEN}[✓ LIVE] {uid} | {name}")
                self.live_count += 1
            else:
                result = {
                    'uid': uid,
                    'status': 'DIE',
                    'name': None,
                    'url': f'https://www.facebook.com/{uid}',
                    'error': error
                }
                print(f"{Fore.RED}[✗ DIE] {uid} | {error}")
                self.die_count += 1
            
            self.results.append(result)
            return result
            
        except Exception as e:
            result = {
                'uid': uid,
                'status': 'DIE',
                'name': None,
                'url': f'https://www.facebook.com/{uid}',
                'error': f'Lỗi: {str(e)}'
            }
            print(f"{Fore.RED}[✗ DIE] {uid} | Error: {str(e)[:50]}")
            self.die_count += 1
            self.results.append(result)
            return result
    
    def check_multiple_uids(self, uids, threads=10):
        """Kiểm tra nhiều UID với threading"""
        print(f"{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}           BẮT ĐẦU KIỂM TRA {len(uids)} UID")
        print(f"{Fore.CYAN}      Phương pháp: Picture Redirect (Nhanh & Chính xác)")
        print(f"{Fore.CYAN}{'='*70}\n")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(self.check_uid, uid): uid for uid in uids}
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"{Fore.RED}Lỗi: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        self.print_summary(duration)
    
    def print_summary(self, duration):
        """In tổng kết kết quả"""
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}                          TỔNG KẾT")
        print(f"{Fore.CYAN}{'='*70}")
        total = self.live_count + self.die_count
        live_percent = (self.live_count / total * 100) if total > 0 else 0
        die_percent = (self.die_count / total * 100) if total > 0 else 0
        
        print(f"{Fore.GREEN}✓ LIVE: {self.live_count} ({live_percent:.1f}%)")
        print(f"{Fore.RED}✗ DIE: {self.die_count} ({die_percent:.1f}%)")
        print(f"{Fore.YELLOW}⏱ Thời gian: {duration:.2f}s")
        print(f"{Fore.MAGENTA}⚡ Tốc độ: {total/duration:.2f} UID/giây")
        print(f"{Fore.CYAN}{'='*70}\n")
    
    def save_results(self, filename='results.txt'):
        """Lưu kết quả ra file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("="*70 + "\n")
                f.write("       KẾT QUẢ KIỂM TRA UID FACEBOOK\n")
                f.write("       Phương pháp: Picture Redirect\n")
                f.write("="*70 + "\n\n")
                
                f.write(f"LIVE: {self.live_count}\n")
                f.write(f"DIE: {self.die_count}\n")
                f.write("="*70 + "\n\n")
                
                # Ghi LIVE
                f.write("DANH SÁCH LIVE:\n")
                f.write("-"*70 + "\n")
                for result in self.results:
                    if result['status'] == 'LIVE':
                        f.write(f"{result['uid']} | {result['name']}\n")
                        f.write(f"   Link: {result['url']}\n\n")
                
                # Ghi DIE
                f.write("\nDANH SÁCH DIE:\n")
                f.write("-"*70 + "\n")
                for result in self.results:
                    if result['status'] == 'DIE':
                        f.write(f"{result['uid']} | {result['error']}\n")
                        f.write(f"   Link: {result['url']}\n\n")
            
            print(f"{Fore.GREEN}✓ Đã lưu kết quả vào file: {filename}")
        
        except Exception as e:
            print(f"{Fore.RED}✗ Lỗi khi lưu file: {e}")
    
    def save_json(self, filename='results.json'):
        """Lưu kết quả dạng JSON"""
        try:
            data = {
                'total': len(self.results),
                'live': self.live_count,
                'die': self.die_count,
                'method': 'picture_redirect',
                'results': self.results
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"{Fore.GREEN}✓ Đã lưu kết quả JSON vào file: {filename}")
        
        except Exception as e:
            print(f"{Fore.RED}✗ Lỗi khi lưu JSON: {e}")
    
    def export_live_only(self, filename='live_uids.txt'):
        """Xuất chỉ các UID LIVE"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for result in self.results:
                    if result['status'] == 'LIVE':
                        f.write(f"{result['uid']}\n")
            
            print(f"{Fore.GREEN}✓ Đã xuất {self.live_count} UID LIVE vào: {filename}")
        except Exception as e:
            print(f"{Fore.RED}✗ Lỗi khi xuất file: {e}")
    
    def export_die_only(self, filename='die_uids.txt'):
        """Xuất chỉ các UID DIE"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for result in self.results:
                    if result['status'] == 'DIE':
                        f.write(f"{result['uid']}\n")
            
            print(f"{Fore.GREEN}✓ Đã xuất {self.die_count} UID DIE vào: {filename}")
        except Exception as e:
            print(f"{Fore.RED}✗ Lỗi khi xuất file: {e}")


def read_uids_from_file(filename):
    """Đọc danh sách UID từ file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            uids = []
            for line in f:
                line = line.strip()
                # Lọc chỉ lấy số
                if line and line.isdigit():
                    uids.append(line)
        return uids
    except Exception as e:
        print(f"{Fore.RED}✗ Lỗi khi đọc file: {e}")
        return []


def main():
    print(f"{Fore.CYAN}{Style.BRIGHT}")
    print("="*70)
    print("              FACEBOOK UID CHECKER - V3.0")
    print("       Phương pháp: Picture Redirect (Cơ chế C#)")
    print("              Nhanh - Chính xác - Không cần Token")
    print("="*70)
    print(f"{Style.RESET_ALL}")
    
    print("\n[1] Nhập UID thủ công")
    print("[2] Đọc UID từ file")
    choice = input("\nChọn chức năng (1/2): ").strip()
    
    uids = []
    
    if choice == '1':
        print("\nNhập các UID cách nhau bởi dấu phẩy hoặc xuống dòng:")
        print("Ví dụ: 100012345678,100087654321")
        print("Gõ 'done' để kết thúc nhập\n")
        
        temp_uids = []
        while True:
            line = input().strip()
            if line.lower() == 'done':
                break
            if not line:
                continue
            
            # Hỗ trợ cả dấu phẩy và xuống dòng
            if ',' in line:
                temp_uids.extend([u.strip() for u in line.split(',') if u.strip()])
            else:
                temp_uids.append(line)
        
        uids = [uid for uid in temp_uids if uid and uid.isdigit()]
    
    elif choice == '2':
        filename = input("\nNhập tên file (mặc định: uids.txt): ").strip()
        if not filename:
            filename = 'uids.txt'
        uids = read_uids_from_file(filename)
    
    else:
        print(f"{Fore.RED}✗ Lựa chọn không hợp lệ!")
        return
    
    if not uids:
        print(f"{Fore.RED}✗ Không có UID hợp lệ để kiểm tra!")
        return
    
    print(f"\n{Fore.YELLOW}📝 Đã tải {len(uids)} UID")
    
    # Hỏi số threads
    try:
        threads_input = input(f"\nSố luồng (threads) - Mặc định 10, tối đa 20: ").strip()
        threads = int(threads_input) if threads_input else 10
        threads = min(max(threads, 1), 20)  # Giới hạn 1-20
    except:
        threads = 10
    
    print(f"{Fore.CYAN}⚙️  Sử dụng {threads} threads\n")
    
    # Khởi tạo checker
    checker = FacebookUIDChecker()
    
    # Kiểm tra UIDs
    checker.check_multiple_uids(uids, threads=threads)
    
    # Lưu kết quả
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}Tùy chọn lưu kết quả:")
    print("[1] Lưu tất cả (TXT + JSON)")
    print("[2] Chỉ lưu UID LIVE")
    print("[3] Chỉ lưu UID DIE")
    print("[4] Lưu cả LIVE và DIE riêng")
    print("[5] Không lưu")
    
    save_choice = input("\nChọn (1/2/3/4/5): ").strip()
    
    if save_choice == '1':
        checker.save_results('results.txt')
        checker.save_json('results.json')
    elif save_choice == '2':
        checker.export_live_only('live_uids.txt')
    elif save_choice == '3':
        checker.export_die_only('die_uids.txt')
    elif save_choice == '4':
        checker.export_live_only('live_uids.txt')
        checker.export_die_only('die_uids.txt')
    
    print(f"\n{Fore.GREEN}{'='*70}")
    print(f"{Fore.GREEN}✓ HOÀN THÀNH!")
    print(f"{Fore.GREEN}{'='*70}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}✗ Đã dừng chương trình!")
    except Exception as e:
        print(f"\n{Fore.RED}✗ Lỗi: {e}")