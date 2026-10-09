# Netgear Orbi: cómo resolver el "wan lan conflict" (panel bloqueado, satélites magenta, malla lenta)

[English](README.md) · [Italiano](README.it.md) · **Español**

Guía práctica para routers Netgear Orbi (probada en **RBR760 / RBK760, firmware V6.3.8.13_1.4.84**) conectados detrás de un módem del operador que usa la misma subred que el Orbi. Otros modelos Orbi usan la misma familia de firmware, así que probablemente también se aplica a ellos.

Los nombres de los menús se indican en inglés, tal como aparecen en la interfaz original del Orbi.

## Síntomas

Probablemente tienes este problema si te pasan varias de estas cosas:

- El panel del Orbi (`orbilogin.com` / `http://10.0.0.1`) muestra una página en blanco, un 404, o una página *"Important Update … IP address was updated to 10.0.0.1"* sin un botón **CONTINUE** que funcione.
- La LAN del Orbi pasó de repente de `192.168.1.x` a `10.0.0.x`.
- Todas las llamadas API del panel devuelven `{"code":8,"msg":"wan lan conflict"}` (visible en las herramientas de desarrollo del navegador, pestaña Red).
- Los satélites tienen el LED **magenta**, o el panel los muestra como simples dispositivos "con cable" con *Number of satellites: 0*.
- La radio de 5 GHz muestra **"Channel 0"**, *5G WLAN: Link down*, y todos los clientes están en 2,4 GHz.
- En *Advanced → Show Statistics* el backhaul es de unos **573 Mbps** (2,4 GHz) en lugar de **~2400 Mbps** (5 GHz). Las habitaciones servidas por un satélite van a ~90 Mbps en lugar de varios cientos.
- El problema **vuelve en cada reinicio** del Orbi.

## Causa

El módem del operador y el Orbi usan ambos `192.168.1.0/24` (muy habitual: muchos módems de operador usan `192.168.1.1`). La WAN del Orbi recibe del módem una dirección `192.168.1.x`, que se solapa con su propia LAN.

El firmware detecta el solapamiento ("wan lan conflict") y:

1. mueve su LAN a `10.0.0.1` como medida de emergencia;
2. redirige el panel a la página `/conflict`, donde se confirma con **CONTINUE**;
3. bloquea la API (`code 8`) hasta que confirmes.

**El bug:** el servidor web del router no sirve `/conflict` (HTTP 404), así que la página de confirmación nunca carga y el panel queda inutilizable. Como la configuración LAN antigua sigue guardada, el conflicto vuelve en cada reinicio. En este estado la malla funciona degradada (radio de 5 GHz caída, satélites sin sincronizar, backhaul en 2,4 GHz).

## Solución rápida

Necesitas dos cosas: (A) superar una vez la página `/conflict` rota, y (B) eliminar el solapamiento de subred para que no vuelva.

### A. Desbloquear el panel

Elige una de estas opciones:

**Opción 1, script de Playwright (probado).** Requiere Node.js.

```bash
cd tools
npm install playwright
npx playwright install chromium
node unlock-conflict.mjs            # o bien: node unlock-conflict.mjs http://<ip-orbi>
```

Se abre una ventana del navegador. Inicia sesión con la contraseña de administrador del Orbi; el script pulsa CONTINUE por ti y muestra la respuesta del router (debe ser `{"code":0,...}`). Deja la ventana abierta y sigue con la parte B.

**Opción 2, proxy con caché.** Requiere Python 3, sin paquetes adicionales.

```bash
python tools/orbi_proxy.py          # ORBI_HOST=<ip-orbi> si no es 10.0.0.1
```

Abre `http://127.0.0.1:8088/index.html`, inicia sesión y pulsa CONTINUE. El proxy responde a `/conflict` con `index.html`, así que la página de confirmación puede cargar. Además guarda en caché el paquete JavaScript de 5-6 MB y hace que el panel sea usable incluso con un Wi-Fi débil (ver [Consejos](#consejos)). La parte de desbloqueo de esta opción no se probó con el router en estado de conflicto; si no funciona, usa la opción 1.

Notas:

- Usa `http://10.0.0.1` en lugar de `orbilogin.com`: con DNS seguro (DoH) activado, el navegador a menudo no resuelve `orbilogin.com`. Con `https://` aparece un error de certificado.
- Llamar a `/dniapi/conflict` a mano (curl, fetch) no funciona: la API requiere un token y una firma calculados por el JavaScript del panel.

### B. Eliminar el solapamiento de subred

Haz al menos una de estas cosas, en este orden de preferencia:

1. **Cambia la LAN del módem del operador** a otra subred, por ejemplo `192.168.10.1/24` (DHCP `192.168.10.2-254`). Algunos módems rechazan ciertos rangos: por ejemplo el TIM Hub (Italia) rechaza `192.168.2.x` con *"Gateway IP should not be in sfp IP Range"*, mientras que acepta `192.168.10.x`. Actualiza también las reservas DHCP y las reglas DMZ / redirección de puertos que apunten al Orbi.
2. **Haz permanente la LAN del Orbi:** *Advanced → Setup → LAN Setup*, mantén o pon una subred distinta a la del módem (p. ej. `10.0.0.1/24`) y pulsa **APPLY**. El router se reinicia y la configuración queda guardada, en lugar de ser solo el recurso de emergencia.
3. Como alternativa, si no necesitas las funciones de enrutamiento del Orbi, ponlo en **modo AP** (*Advanced → Advanced Setup → Router / AP Mode*), así no tiene una subred LAN propia.

### C. Renovar la dirección WAN del Orbi

Tras cambiar la subred del módem, el Orbi mantiene durante horas la concesión WAN antigua (`192.168.1.x`), incluso tras reiniciar, e Internet deja de funcionar. Se resuelve con:

*Advanced → Home → **Connection Status*** (se abre en una pestaña nueva) → **Release** → **Renew**.

Ahora la WAN debe mostrar una dirección en la nueva subred (p. ej. `192.168.10.x`) con el módem como puerta de enlace y DNS.

### D. Reiniciar una vez y esperar

Reinicia una vez el router Orbi (*Advanced → Home → Reboot*, o desde la app Orbi). Después revisa *Advanced → Home → Show Statistics* y *Attached Devices*:

- 5G WLAN debe mostrar ~2400M y un canal real (p. ej. *36+40+…+64, up to 2401 Mbps*), no *Channel 0*.
- Los satélites deben aparecer en **Connected Satellites**, no como clientes con cable.
- **Ten paciencia:** durante los primeros ~15 minutos tras el reinicio los satélites pueden seguir en el backhaul de 2,4 GHz (573M). En nuestro caso, después pasaron solos a 5 GHz (2401M).

Guardar la configuración inalámbrica sin cambios, o cambiar el canal de 5 GHz, **no** reactivó la radio de 5 GHz; hizo falta un reinicio tras eliminar el conflicto.

## Resultados (un caso real)

| | Antes | Después |
|---|---|---|
| Panel Orbi | bloqueado en `/conflict` 404 | funciona |
| Radio 5 GHz | Channel 0, link down | 36-64, 2401 Mbps |
| Satélites | magenta / "con cable", 0 sincronizados | 2 conectados, backhaul "good" |
| Backhaul | 573 Mbps (2,4 GHz) | 2401 Mbps (5 GHz) |
| Descarga en una habitación con satélite (por cable) | ~90 Mbps | ~200-300 Mbps (servidores de prueba extranjeros) |

## Consejos

- **¿Satélite todavía magenta?** No fuerces *Add Orbi Satellite* una y otra vez: las sincronizaciones repetidas reorganizan la malla y empeoran todo. Pulsa primero el botón **Sync** del satélite y luego *SYNC* en el panel antes de 2 minutos, idealmente con el satélite cerca del router.
- **¿El panel nunca termina de cargar por Wi-Fi?** El paquete JavaScript del panel pesa 5-6 MB y falla en enlaces con pérdidas. `tools/orbi_proxy.py` lo guarda en caché en la primera carga y después el panel abre en 1-3 s. Puedes lanzar un proxy por dispositivo, p. ej. `ORBI_HOST=10.0.0.11 PROXY_PORT=8089` para un satélite.
- **Canales DFS.** Con 160 MHz el fronthaul de 5 GHz usa los canales 52-64 (DFS); la detección de radar puede provocar cambios de canal repentinos y cortes. Si ves desconexiones aleatorias, prueba 80 MHz en un canal fijo (36 o 44).
- **¿PC con Windows atascado a 11 Mbps en 2,4 GHz?** Revisa la propiedad avanzada del adaptador Wi-Fi *"2.4G Wireless Mode"*: el valor `IEEE 802.11b` fuerza velocidades antiguas. Debe ser `IEEE 802.11b/g/n/ax`.
- **Pruebas de velocidad:** usa un servidor de tu país; los servidores lejanos limitan el resultado muy por debajo de una línea de 1 gigabit.

## Contenido del repositorio

| Archivo | Uso |
|---|---|
| `tools/unlock-conflict.mjs` | Script de Playwright que evita la página `/conflict` rota y pulsa CONTINUE |
| `tools/orbi_proxy.py` | Proxy local con caché para el panel del Orbi (solo biblioteca estándar de Python 3) |

## Aviso

Proyecto no afiliado a Netgear. Cambiar la configuración del router puede cortar tu conexión; antes de cambiar la LAN del módem asegúrate de poder acceder a él por cable y apunta los valores anteriores. Úsalo bajo tu propia responsabilidad.

## Licencia

[MIT](LICENSE) © lambdagw
