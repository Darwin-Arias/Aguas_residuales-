import mysql.connector
from datetime import datetime, time
import tkinter as tk
from tkinter import messagebox

HORA_ENTRADA_OFICIAL = time(8, 0)

def obtener_conexion():
    return mysql.connector.connect(
        host="localhost",
        user="USUARIO_SEGURO",
        password="CONTRASEÑA_SEGURA",
        database="registro_asistencia_inatrans"
    )

def calcular_atraso(hora_ingreso_str):
    hora_i = datetime.strptime(hora_ingreso_str, "%H:%M").time()
    if hora_i > HORA_ENTRADA_OFICIAL:
        hoy = datetime.now().date()
        dt_oficial = datetime.combine(hoy, HORA_ENTRADA_OFICIAL)
        dt_ingreso = datetime.combine(hoy, hora_i)
        diferencia = dt_ingreso - dt_oficial
        return int(diferencia.total_seconds() / 60)
    return 0

def calcular_jornada(I, SC, RC, E):
    fmt = "%H:%M"
    hoy = datetime.now().date()
    dt_i = datetime.strptime(f"{hoy} {I}", f"{hoy} {fmt}")
    dt_sc = datetime.strptime(f"{hoy} {SC}", f"{hoy} {fmt}")
    dt_rc = datetime.strptime(f"{hoy} {RC}", f"{hoy} {fmt}")
    dt_e = datetime.strptime(f"{hoy} {E}", f"{hoy} {fmt}")
    return (dt_sc - dt_i) + (dt_e - dt_rc)

def marcar_ahora(entry):
    ahora = datetime.now().strftime("%H:%M")
    entry.delete(0, tk.END)
    entry.insert(0, ahora)

def enviar_datos():
    id_emp = entry_id.get().strip()
    h_i = entry_i.get().strip()
    h_sc = entry_sc.get().strip()
    h_rc = entry_rc.get().strip()
    h_e = entry_e.get().strip()

    if not id_emp:
        messagebox.showwarning("Atención", "Ingrese ID de empleado")
        return

    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        fecha_hoy = datetime.now().date()

        cursor.execute("SELECT nombre_completo FROM empleados WHERE id_empleado = %s", (id_emp,))
        empleado = cursor.fetchone()
        
        if not empleado:
            messagebox.showerror("Error", "ID no encontrado")
            return
        
        nombre_trabajador = empleado[0]

        cursor.execute("SELECT id_registro FROM registro_asistencia WHERE id_empleado_fk = %s AND fecha = %s", (id_emp, fecha_hoy))
        registro = cursor.fetchone()

        if not registro:
            if not h_i:
                messagebox.showwarning("Atención", "Debe marcar el Ingreso primero")
                return
            
            minutos_atraso = calcular_atraso(h_i)
            sql = "INSERT INTO registro_asistencia (id_empleado_fk, fecha, ingreso, atraso_minutos) VALUES (%s, %s, %s, %s)"
            val = (id_emp, fecha_hoy, f"{fecha_hoy} {h_i}", minutos_atraso)
            cursor.execute(sql, val)
            msg = f"¡Hola {nombre_trabajador}!\nIngreso registrado correctamente."
            if minutos_atraso > 0:
                msg += f"\nNota: {minutos_atraso} min. de atraso."
        else:
            id_reg = registro[0]
            if h_e:
                sql = "UPDATE registro_asistencia SET egreso = %s WHERE id_registro = %s"
                cursor.execute(sql, (f"{fecha_hoy} {h_e}", id_reg))
                msg = f"Salida registrada para {nombre_trabajador}."
            elif h_rc:
                sql = "UPDATE registro_asistencia SET regreso_colacion = %s WHERE id_registro = %s"
                cursor.execute(sql, (f"{fecha_hoy} {h_rc}", id_reg))
                msg = "Regreso de colación registrado."
            elif h_sc:
                sql = "UPDATE registro_asistencia SET salida_colacion = %s WHERE id_registro = %s"
                cursor.execute(sql, (f"{fecha_hoy} {h_sc}", id_reg))
                msg = "Salida a colación registrada."
            else:
                msg = "Ya tienes un registro de ingreso hoy."

        conn.commit()
        messagebox.showinfo("Éxito", msg)

    except Exception as e:
        messagebox.showerror("Error", f"Error: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

root = tk.Tk()
root.title("Inatrans - Registro Oficial")
root.geometry("350x500")

tk.Label(root, text="ID Empleado:", font=('Arial', 10, 'bold')).pack(pady=10)
entry_id = tk.Entry(root, justify='center', font=('Arial', 12))
entry_id.pack()

def crear_fila(texto):
    frame = tk.Frame(root)
    frame.pack(pady=5)
    tk.Label(frame, text=texto, width=15).grid(row=0, column=0)
    ent = tk.Entry(frame, width=10)
    ent.grid(row=0, column=1)
    tk.Button(frame, text="Marcar", command=lambda: marcar_ahora(ent)).grid(row=0, column=2, padx=5)
    return ent

entry_i = crear_fila("Ingreso:")
entry_sc = crear_fila("Salida Colación:")
entry_rc = crear_fila("Regreso Colación:")
entry_e = crear_fila("Egreso:")

btn_guardar = tk.Button(root, text="GUARDAR REGISTRO", command=enviar_datos, 
                        bg="#007bff", fg="white", font=('Arial', 10, 'bold'), height=2, width=25)
btn_guardar.pack(pady=30)

root.mainloop()