import mysql.connector
import tkinter as tk
from tkinter import messagebox, ttk

def conectar():
    return mysql.connector.connect(
        host="localhost", user="root", password="cjkl7615", database="registro_asistencia_inatrans"
    )

def cargar_datos():
    for item in tabla.get_children():
        tabla.delete(item)
    try:
        conn = conectar()
        cursor = conn.cursor()
        query = """
            SELECT e.id_empleado, e.rut, e.nombre_completo, e.cargo, 
                   COALESCE(SUM(r.atraso_minutos), 0) as total_atraso
            FROM empleados e
            LEFT JOIN registro_asistencia r ON e.id_empleado = r.id_empleado_fk
            GROUP BY e.id_empleado, e.rut, e.nombre_completo, e.cargo
        """
        cursor.execute(query)
        for fila in cursor.fetchall():
            tabla.insert("", tk.END, values=fila)
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Error al cargar: {e}")

def agregar_empleado():
    rut, nombre, cargo = entry_rut.get(), entry_nombre.get(), entry_cargo.get()
    if not rut or not nombre:
        messagebox.showwarning("Atención", "Rut y nombre son obligatorios")
        return
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO empleados (rut, nombre_completo, cargo) VALUES (%s, %s, %s)", (rut, nombre, cargo))
        conn.commit()
        conn.close()
        messagebox.showinfo("Éxito", "Empleado agregado correctamente")
        cargar_datos()
    except Exception as e:
        messagebox.showerror("Error", str(e))

def eliminar_empleado():
    selected = tabla.selection()
    if not selected:
        messagebox.showwarning("Atención", "Selecciona un empleado")
        return
    id_emp = tabla.item(selected)['values'][0]
    if messagebox.askyesno("Confirmar", "¿Seguro que quieres eliminar a este empleado?"):
        try:
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM empleados WHERE id_empleado = %s", (id_emp,))
            conn.commit()
            conn.close()
            cargar_datos()
        except Exception:
            messagebox.showerror("Error", "No se pudo eliminar (el empleado tiene registros de asistencia)")

# Interfaz RR.HH.
root = tk.Tk()
root.title("Inatrans - Panel de Control RR.HH.")
root.geometry("750x550")

frame_form = tk.LabelFrame(root, text="Registro de Nuevo Personal", padx=10, pady=10)
frame_form.pack(pady=10, padx=10, fill="x")

tk.Label(frame_form, text="Rut:").grid(row=0, column=0)
entry_rut = tk.Entry(frame_form); entry_rut.grid(row=0, column=1)
tk.Label(frame_form, text="Nombre:").grid(row=0, column=2)
entry_nombre = tk.Entry(frame_form); entry_nombre.grid(row=0, column=3)
tk.Label(frame_form, text="Cargo:").grid(row=0, column=4)
entry_cargo = tk.Entry(frame_form); entry_cargo.grid(row=0, column=5)

tk.Button(frame_form, text="Agregar", command=agregar_empleado, bg="#28a745", fg="white").grid(row=0, column=6, padx=10)

columnas = ("ID", "RUT", "Nombre", "Cargo", "Atraso Acum. (min)")
tabla = ttk.Treeview(root, columns=columnas, show="headings")
for col in columnas:
    tabla.heading(col, text=col)
    tabla.column(col, width=120)
tabla.column("ID", width=40)
tabla.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

tk.Button(root, text="Eliminar Seleccionado", command=eliminar_empleado, bg="#dc3545", fg="white").pack(pady=10)

cargar_datos()
root.mainloop()