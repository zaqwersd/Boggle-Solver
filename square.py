import os
import json
import math
import datetime
import tkinter as tk
from tkinter import messagebox

# ---- 一、词典预处理 ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DICT_PATH = os.path.join(BASE_DIR, "Dictionary.txt")
GRID_PATH = os.path.join(BASE_DIR, "last_grid.json")
LOG_PATH = os.path.join(BASE_DIR, "dict_log.txt")


def preprocess_dictionary(path: str = DICT_PATH):
    if not os.path.exists(path):
        messagebox.showerror("错误", f"未找到词典文件：{path}")
        return set(), set()

    with open(path, "r", encoding="utf-8") as f:
        words = [w.strip().upper() for w in f if w.strip()]

    unique = sorted(set(words))
    with open(path, "w", encoding="utf-8") as f:
        for w in unique:
            f.write(w + "\n")

    dict_set = set(unique)
    prefix_set = set()
    for w in dict_set:
        for i in range(1, len(w)):
            prefix_set.add(w[:i])
    return dict_set, prefix_set

# ---- 二、Boggle 求解函数 ----
def solve_boggle(grid, dict_set, prefix_set, min_len: int = 4):
    R, C = 4, 4
    found = {}
    visited = [[False] * C for _ in range(R)]

    def dfs(r, c, cur, path):
        if r < 0 or r >= R or c < 0 or c >= C or visited[r][c]:
            return
        letter = grid[r][c]
        if not letter:
            return
        cur += letter
        if cur not in prefix_set and cur not in dict_set:
            return
        visited[r][c] = True
        path.append((r, c))
        if len(cur) >= min_len and cur in dict_set and cur not in found:
            found[cur] = list(path)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                dfs(r + dr, c + dc, cur, path)
        path.pop()
        visited[r][c] = False

    for i in range(R):
        for j in range(C):
            dfs(i, j, "", [])
    return found

# ---- 三、主界面 ----
class BoggleApp:
    def __init__(self, master):
        self.master = master
        master.title("Boggle 可视化求解器")
        master.minsize(700, 500)

        self.dict_set, self.prefix_set = preprocess_dictionary()
        if not self.dict_set:
            master.destroy()
            return

        frame_left = tk.Frame(master)
        frame_left.grid(row=0, column=0, padx=10, pady=10)

        self.cell_size = 60
        canvas_size = self.cell_size * 4
        self.canvas = tk.Canvas(
            frame_left, width=canvas_size, height=canvas_size, bg="white"
        )
        self.canvas.grid(row=0, column=0, columnspan=2)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        for i in range(5):
            pos = i * self.cell_size
            self.canvas.create_line(0, pos, canvas_size, pos)
            self.canvas.create_line(pos, 0, pos, canvas_size)

        self.entries = []
        self.entry_window_ids = []
        for r in range(4):
            row = []
            for c in range(4):
                e = tk.Entry(frame_left, width=2, font=("Arial", 24), justify="center")
                e.bind("<KeyRelease>", self.on_key_release)
                x = c * self.cell_size + self.cell_size / 2
                y = r * self.cell_size + self.cell_size / 2
                win_id = self.canvas.create_window(
                    x, y, window=e,
                    width=self.cell_size - 4, height=self.cell_size - 4
                )
                self.entry_window_ids.append(win_id)
                row.append(e)
            self.entries.append(row)

        # Solve button
        btn = tk.Button(frame_left, text="查找所有单词", command=self.on_solve,
                        font=("微软雅黑", 15), width=15, height=1)
        btn.grid(row=1, column=0, columnspan=2, pady=10)

        # New word entry
        self.entry_new_word = tk.Entry(frame_left, width=25, font=("Consolas", 15))
        self.entry_new_word.grid(row=2, column=0, columnspan=2, pady=(0, 5))

        # Add/Delete/History buttons
        btn_frame = tk.Frame(frame_left)
        btn_frame.grid(row=3, column=0, columnspan=2)

        btn_add_word = tk.Button(btn_frame, text="添加到词典", command=self.add_new_word,
                                 font=("微软雅黑", 12), width=10)
        btn_add_word.pack(side=tk.LEFT, padx=(0, 5))

        btn_delete_word = tk.Button(btn_frame, text="删除该单词", command=self.delete_word,
                                     font=("微软雅黑", 12), width=10)
        btn_delete_word.pack(side=tk.LEFT, padx=(0, 5))

        btn_history = tk.Button(btn_frame, text="历史记录", command=self.view_history,
                                 font=("微软雅黑", 12), fg="blue", bd=0, cursor="hand2")
        btn_history.pack(side=tk.LEFT)

        # Word count label
        self.label_word_count = tk.Label(frame_left, text=f"词典总词数: {len(self.dict_set)}", font=("微软雅黑", 12))
        self.label_word_count.grid(row=4, column=0, columnspan=2, pady=(5, 0))

        # Right frame for results
        frame_right = tk.Frame(master)
        frame_right.grid(row=0, column=1, sticky="nsew", padx=(10, 10), pady=(10, 30))
        master.grid_columnconfigure(1, weight=1)
        master.grid_rowconfigure(0, weight=1)
        frame_right.grid_propagate(False)

        tk.Label(frame_right, text="找到的单词：").pack()
        self.listbox = tk.Listbox(frame_right, width=20, height=20, font=("Consolas", 12))
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        self.found = {}
        self.grid = [["" for _ in range(4)] for _ in range(4)]
        self.load_last_grid()

    def timestamp(self):
        now = datetime.datetime.now()
        return f"{now.year}/{now.month}/{now.day} {now.hour:02d}:{now.minute:02d}"

    def add_new_word(self):
        word = self.entry_new_word.get().strip().upper()
        if not word.isalpha() or len(word) < 4:
            messagebox.showwarning("无效输入", "请输入长度不小于4的英文单词")
            return
        if word in self.dict_set:
            messagebox.showinfo("提示", f"单词 '{word.lower()}' 已在词典中")
            return
        try:
            with open(DICT_PATH, "a", encoding="utf-8") as f:
                f.write(word + "\n")
            with open(LOG_PATH, "a", encoding="utf-8") as log:
                log.write(f"{self.timestamp()} ADD: {word}\n")
            self.dict_set.add(word)
            for i in range(1, len(word)):
                self.prefix_set.add(word[:i])
            self.label_word_count.config(text=f"词典总词数: {len(self.dict_set)}")
            self.entry_new_word.delete(0, tk.END)
            messagebox.showinfo("成功", f"单词 '{word.lower()}' 已添加")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def delete_word(self):
        word = self.entry_new_word.get().strip().upper()
        if not word:
            messagebox.showwarning("无效输入", "请输入要删除的单词")
            return
        if word not in self.dict_set:
            messagebox.showinfo("提示", f"单词 '{word.lower()}' 不在词典中")
            return
        try:
            with open(DICT_PATH, "r", encoding="utf-8") as f:
                words = [w.strip().upper() for w in f if w.strip().upper() != word]
            with open(DICT_PATH, "w", encoding="utf-8") as f:
                for w in sorted(set(words)):
                    f.write(w + "\n")
            with open(LOG_PATH, "a", encoding="utf-8") as log:
                log.write(f"{self.timestamp()} DEL: {word}\n")
            self.dict_set.discard(word)
            self.prefix_set.clear()
            for w in self.dict_set:
                for i in range(1, len(w)):
                    self.prefix_set.add(w[:i])
            self.label_word_count.config(text=f"词典总词数: {len(self.dict_set)}")
            self.entry_new_word.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def view_history(self):
        win = tk.Toplevel(self.master)
        win.title("历史记录")
        win.geometry("400x300")
        win.configure(bg="grey90")
        outer = tk.Frame(win, bg="white", bd=1, relief="solid")
        outer.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        if not os.path.exists(LOG_PATH):
            tk.Label(outer, text="无历史记录", bg="white").pack(padx=10, pady=10)
            return
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]

        for idx, ln in enumerate(lines):
            parts = ln.split()
            if len(parts) < 4:
                continue
            date, time_str, op_token = parts[0], parts[1], parts[2]
            word = " ".join(parts[3:])
            op = op_token.rstrip(":")
            op_cn = '               添加' if op == 'ADD' else '               删除'
            ts_display = f"{date} {time_str}"
            txt = f"{ts_display} {op_cn}: {word.lower()}"

            row = tk.Frame(outer, bg="white")
            row.pack(fill=tk.X, padx=10, pady=2)
            lbl = tk.Label(row, text=txt, bg="white")
            lbl.pack(side=tk.LEFT)
            # 创建一个看起来像链接的 Label
            lbl_undo = tk.Label(row,
                                text="撤销",
                                font=("微软雅黑", 10, "underline"),  # 加下划线更像超链接
                                fg="blue",
                                cursor="hand2",
                                bg="white")  # 保持和父容器背景一致

            # 绑定点击事件
            lbl_undo.bind(
                "<Button-1>",
                lambda e, i=idx, o=op, w=word, winn=win: self.undo_history(i, o, w, winn)
            )

            lbl_undo.pack(side=tk.RIGHT)

    def undo_history(self, index, op, word, win):
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = [ln for ln in f.readlines()]
        if index < 0 or index >= len(lines):
            return
        entry = lines.pop(index).strip()
        if op == 'ADD':
            self.dict_set.discard(word)
        else:
            self.dict_set.add(word)
        with open(DICT_PATH, "w", encoding="utf-8") as f:
            for w in sorted(self.dict_set):
                f.write(w + "\n")
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.writelines(lines)
        self.prefix_set.clear()
        for w in self.dict_set:
            for i in range(1, len(w)):
                self.prefix_set.add(w[:i])
        self.label_word_count.config(text=f"词典总词数: {len(self.dict_set)}")
        win.destroy()
        self.view_history()

    def on_canvas_click(self, event):
        self.clear_path()

    def load_last_grid(self):
        if not os.path.exists(GRID_PATH):
            return
        try:
            with open(GRID_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, list) and len(saved) == 4:
                for i in range(4):
                    for j in range(4):
                        text = saved[i][j]
                        self.entries[i][j].insert(0, text)
                self.grid = saved
        except Exception:
            pass

    def on_key_release(self, event):
        text = event.widget.get().upper()
        if len(text) > 1:
            text = text[-1]
        if text and not text.isalpha():
            text = ""
        event.widget.delete(0, tk.END)
        event.widget.insert(0, text)

    def read_grid(self):
        grid = []
        for r in range(4):
            row = []
            for c in range(4):
                row.append(self.entries[r][c].get().strip().upper())
            grid.append(row)
        return grid

    def save_grid(self):
        try:
            with open(GRID_PATH, "w", encoding="utf-8") as f:
                json.dump(self.grid, f)
        except Exception:
            pass

    def clear_path(self):
        self.canvas.delete("path")
        self.toggle_entries(True)

    def toggle_entries(self, show: bool):
        state = "normal" if show else "hidden"
        for win_id in self.entry_window_ids:
            self.canvas.itemconfigure(win_id, state=state)

    def on_solve(self):
        self.clear_path()
        self.grid = self.read_grid()
        self.save_grid()
        self.found = solve_boggle(self.grid, self.dict_set, self.prefix_set)

        self.listbox.delete(0, tk.END)
        self.listbox.configure(fg="black")
        if not self.found:
            self.listbox.insert(tk.END, "<未找到任何单词>")
            return

        total_words = len(self.found)
        self.listbox.insert(tk.END, f"{total_words} words found in total")
        self.listbox.itemconfig(tk.END, {"fg": "red"})

        groups = {}
        for w in self.found:
            groups.setdefault(len(w), []).append(w)
        for idx, length in enumerate(sorted(groups)):
            words = sorted(groups[length])
            header = f"{length} letter words ({len(words)} words found):"
            self.listbox.insert(tk.END, header)
            self.listbox.itemconfig(tk.END, {"fg": "blue"})
            for w in words:
                self.listbox.insert(tk.END, w)
            if idx != len(groups) - 1:
                self.listbox.insert(tk.END, "")

    def on_select(self, event):
        sel = self.listbox.curselection()
        if not sel or not self.found:
            return
        word = self.listbox.get(sel[0])
        if word not in self.found:
            return

        self.clear_path()
        self.toggle_entries(False)

        for r in range(4):
            for c in range(4):
                letter = self.grid[r][c]
                x = c * self.cell_size + self.cell_size / 2
                y = r * self.cell_size + self.cell_size / 2
                self.canvas.create_text(
                    x, y, text=letter, font=("Arial", 24), fill="black", tags="path"
                )

        path = self.found[word]
        radius = 20
        coords = [
            (c * self.cell_size + self.cell_size / 2, r * self.cell_size + self.cell_size / 2)
            for (r, c) in path
        ]

        for idx, (x, y) in enumerate(coords, start=1):
            self.canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                outline="green", width=2, tags="path"
            )
            offset = radius * 0.6
            self.canvas.create_text(
                x + 1.6*offset, y - 1.6*offset,
                text=str(idx), font=("Arial", 12, "bold"), fill="blue", tags="path"
            )

        def get_edge_point(x0, y0, x1, y1, r):
            dx, dy = x1 - x0, y1 - y0
            length = math.hypot(dx, dy)
            if length == 0:
                return x0, y0
            ux, uy = dx / length, dy / length
            return x0 + ux * r, y0 + uy * r

        for i in range(len(coords) - 1):
            x0, y0 = coords[i]
            x1, y1 = coords[i + 1]
            sx, sy = get_edge_point(x0, y0, x1, y1, radius)
            ex, ey = get_edge_point(x1, y1, x0, y0, radius)
            self.canvas.create_line(sx, sy, ex, ey, width=2, fill="green", tags="path")

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("700x500")
    app = BoggleApp(root)
    root.mainloop()
