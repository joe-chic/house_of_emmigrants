#include "sys/types.h"
#include "sys/stat.h"
#include "unistd.h"
#include "stdio.h"
#include "stdlib.h"
#include "string.h"
#include "fcntl.h"

int main() {
    char mensaje[] = "Hola desde el proceso padre";
    char buffer[100];

    // Crear FIFO
    if (mkfifo("mi_fifo", 0666) == -1) {
        perror("Error al crear el FIFO");
        return 1;
    }

    pid_t pid = fork();  // Crear proceso hijo

    if (pid < 0) {
        perror("Error al hacer fork");
        return 1;
    }

    if (pid == 0) {  // Proceso hijo
        int fd = open("mi_fifo", O_RDONLY);  // Se abre FIFO para lectura
        if (fd == -1) {
            perror("Error al abrir el FIFO para lectura");
            return 1;
        }
        read(fd, buffer, sizeof(buffer));  // Leer del FIFO
        printf("Hijo recibió: %s\n", buffer);
        close(fd);  // Se cierra el FIFO
    } else {  // Proceso padre
        int fd = open("mi_fifo", O_WRONLY);  // Abrir FIFO para escritura
        if (fd == -1) {
            perror("Error al abrir el FIFO para escritura");
            return 1;
        }
        write(fd, mensaje, strlen(mensaje) + 1);  // Escribir en el FIFO
        close(fd);  // Cerrar FIFO
    }

    // Se elimina el FIFO
    unlink("mi_fifo");

    return 0;
}