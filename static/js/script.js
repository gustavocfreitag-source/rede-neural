// ======================================
// USUÁRIO
// ======================================

const usuario = JSON.parse(
    localStorage.getItem("usuarioLogado")
);

if(!usuario){

    window.location.href = "/login";
}

document.getElementById("nomeUsuario").innerText =
    usuario.nome || "Usuário";

document.getElementById("tipoUsuario").innerText =
    usuario.tipo || "Paciente";

document.getElementById("modoBadge").innerText =
    (usuario.tipo || "Paciente").toUpperCase();

// ======================================
// CHAT
// ======================================

function addMsg(texto, tipo="ai-message"){

    const chat = document.getElementById("chat");

    const wrapper = document.createElement("div");

    wrapper.className = "message-wrapper";

    const msg = document.createElement("div");

    msg.className = "message " + tipo;

    msg.textContent = texto;

    wrapper.appendChild(msg);

    chat.appendChild(wrapper);

    chat.scrollTop = chat.scrollHeight;
}

// ======================================
// ÁUDIO
// ======================================

let audioAtual = null;
let recognition = null;
let gravando = false;

function tocarAudio(url){

    if(!url){

        addMsg("Áudio não disponível.");

        return;
    }

    if(audioAtual){

        audioAtual.pause();
    }

    audioAtual = new Audio(url);

    audioAtual.play()
    .catch(err=>{

        console.error(err);

        addMsg("Erro ao reproduzir áudio.");

    });
}

function pausarAudio(){

    if(audioAtual){

        audioAtual.pause();
    }
}

function inicializarReconhecimento(){

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    if(!SpeechRecognition){

        return null;
    }

    const rec = new SpeechRecognition();

    rec.lang = 'pt-BR';
    rec.interimResults = true;
    rec.continuous = false;

    rec.onresult = event => {

        let texto = '';

        for(let i = event.resultIndex; i < event.results.length; i++){

            texto += event.results[i][0].transcript;
        }

        const input = document.getElementById('input');

        if(input){

            input.value = texto;
        }
    };

    rec.onend = () => {

        gravando = false;

        atualizarBotaoGravacao();

        addMsg('Gravação finalizada. Verifique o texto e envie.');
    };

    rec.onerror = event => {

        console.error('Erro reconhecimento de voz:', event.error);

        gravando = false;

        atualizarBotaoGravacao();

        addMsg('Erro na gravação de voz. Use Chrome/Edge e permita o microfone.');
    };

    return rec;
}

function atualizarBotaoGravacao(){

    const btn = document.getElementById('btnRecord');

    if(!btn) return;

    if(gravando){

        btn.classList.add('recording');

        btn.textContent = '⏹';

        btn.title = 'Parar gravação';

    }else{

        btn.classList.remove('recording');

        btn.textContent = '🎙';

        btn.title = 'Gravar áudio';
    }
}

function toggleGravacao(){

    if(!recognition){

        addMsg('Gravação de voz não suportada neste navegador.');

        return;
    }

    if(gravando){

        recognition.stop();

        return;
    }

    try{

        recognition.start();

        gravando = true;

        atualizarBotaoGravacao();

        addMsg('Gravação iniciada. Fale agora.');

    }catch(err){

        console.error('Erro ao iniciar gravação:', err);

        addMsg('Não foi possível iniciar a gravação.');

    }
}

recognition = inicializarReconhecimento();

// ======================================
// LOGOUT
// ======================================

function logout(){

    localStorage.removeItem("usuarioLogado");

    window.location.href = "/login";
}

// ======================================
// DADOS
// ======================================

let etapa = 0;

let dados = {};

// ======================================
// NOVA TRIAGEM
// ======================================

function novaTriagem(){

    etapa = 0;

    dados = {};

    document.getElementById("chat").innerHTML = "";

    iniciarFluxo();
}

// ======================================
// INICIAR
// ======================================

function iniciarFluxo(){

    if(usuario.tipo === "Autoatendimento"){

        addMsg("Olá! Vamos iniciar sua triagem.");

        addMsg("Qual sua idade?");

    }else{

        addMsg("Triagem técnica iniciada.");

        addMsg("Informe o nome do paciente.");
    }
}

iniciarFluxo();

// ======================================
// VALIDAR
// ======================================

function numeroValido(valor,min,max){

    const n = Number(valor);

    return !isNaN(n) &&
           n >= min &&
           n <= max;
}

// ======================================
// ENVIAR
// ======================================

async function enviar(){

    const input = document.getElementById("input");

    const texto = input.value.trim();

    if(!texto) return;

    addMsg(texto,"user-message");

    input.value = "";

    // AUTOATENDIMENTO

    if(usuario.tipo === "Autoatendimento"){

        if(etapa === 0){

            if(!numeroValido(texto,0,120)){

                addMsg("Idade inválida.");

                return;
            }

            dados.idade = texto;

            addMsg("Qual seu peso em kg?");

            etapa++;

            return;
        }

        if(etapa === 1){

            dados.peso = texto;

            addMsg("Qual sua altura em cm?");

            etapa++;

            return;
        }

        if(etapa === 2){

            dados.altura = texto;

            addMsg("Quais sintomas você sente?");

            etapa++;

            return;
        }

        if(etapa === 3){

            dados.sintomas = texto;

            addMsg("Há quanto tempo está com os sintomas?");

            etapa++;

            return;
        }

        if(etapa === 4){

            dados.tempo = texto;

            await finalizarTriagem();

            return;
        }
    }

    // TÉCNICO

    else{

        if(etapa === 0){

            dados.nome = texto;

            addMsg("Informe o CPF do paciente.");

            etapa++;

            return;
        }

        if(etapa === 1){

            dados.cpf = texto;

            addMsg("Qual a idade do paciente?");

            etapa++;

            return;
        }

        if(etapa === 2){

            if(!numeroValido(texto,0,120)){

                addMsg("Idade inválida.");

                return;
            }

            dados.idade = texto;

            addMsg("Descreva os sintomas do paciente.");

            etapa++;

            return;
        }

        if(etapa === 3){

            dados.sintomas = texto;

            addMsg("Informe a pressão arterial.");

            etapa++;

            return;
        }

        if(etapa === 3){

            dados.pressao = texto;

            addMsg("Informe a frequência cardíaca.");

            etapa++;

            return;
        }

        if(etapa === 4){

            dados.fc = texto;

            addMsg("Informe a frequência respiratória.");

            etapa++;

            return;
        }

        if(etapa === 5){

            dados.fr = texto;

            addMsg("Informe a temperatura corporal.");

            etapa++;

            return;
        }

        if(etapa === 6){

            dados.temperatura = texto;

            addMsg("Informe a saturação de O2.");

            etapa++;

            return;
        }

        if(etapa === 7){

            dados.saturacao = texto;

            await finalizarTriagem();

            return;
        }
    }
}

// ======================================
// FINALIZAR
// ======================================

async function finalizarTriagem(){

    addMsg("Analisando dados...");

    let resumo = "";

    if(usuario.tipo === "Autoatendimento"){

        resumo = `
MODO: AUTOATENDIMENTO

IDADE: ${dados.idade}
PESO: ${dados.peso}
ALTURA: ${dados.altura}
SINTOMAS: ${dados.sintomas}
TEMPO: ${dados.tempo}
`;

    }else{

        resumo = `
MODO: TRIAGEM TÉCNICA

NOME: ${dados.nome}
CPF: ${dados.cpf}
IDADE: ${dados.idade}
SINTOMAS: ${dados.sintomas}
PRESSÃO: ${dados.pressao}
FREQUÊNCIA CARDÍACA: ${dados.fc}
FREQUÊNCIA RESPIRATÓRIA: ${dados.fr}
TEMPERATURA: ${dados.temperatura}
SATURAÇÃO: ${dados.saturacao}
`;
    }

    try{

        const res = await fetch("/chat",{

            method:"POST",

            headers:{
                "Content-Type":"application/json"
            },

            body:JSON.stringify({
                mensagem:resumo
            })

        });

        const data = await res.json();

        if(res.ok && data.resposta){

            addMsg(data.resposta);

            // AUDIO

            if(data.audio){

                const chat =
                    document.getElementById("chat");

                const wrapper =
                    document.createElement("div");

                wrapper.className =
                    "message-wrapper";

                const controls =
                    document.createElement("div");

                controls.className =
                    "audio-controls";

                // PLAY

                const btnPlay =
                    document.createElement("button");

                btnPlay.className =
                    "audio-btn";

                btnPlay.innerText =
                    "🔊 Tocar";

                btnPlay.onclick = ()=>{

                    tocarAudio(data.audio);
                };

                // PAUSE

                const btnPause =
                    document.createElement("button");

                btnPause.className =
                    "audio-btn";

                btnPause.innerText =
                    "⏸ Pausar";

                btnPause.onclick = ()=>{

                    pausarAudio();
                };

                controls.appendChild(btnPlay);

                controls.appendChild(btnPause);

                wrapper.appendChild(controls);

                chat.appendChild(wrapper);

                chat.scrollTop =
                    chat.scrollHeight;
            }

        }else{

            addMsg(
                data.erro ||
                "Erro ao processar triagem."
            );
        }

    }catch(erro){

        console.error(erro);

        addMsg("Erro no servidor.");
    }

    etapa = 0;

    dados = {};

    setTimeout(()=>{

        addMsg("-----------------------");

        iniciarFluxo();

    },1500);
}

// ======================================
// ENTER
// ======================================

document
.getElementById("input")
.addEventListener("keypress",function(e){

    if(e.key === "Enter"){

        enviar();
    }

});
// ======================================
// EVENTOS DOS BOTÕES
// ======================================

document
.getElementById("btnNovaTriagem")
.addEventListener("click", novaTriagem);

document
.getElementById("btnLogout")
.addEventListener("click", logout);

// ======================================
// BOTÃO ENVIAR
// ======================================

document
.getElementById("btnEnviar")
.addEventListener("click", enviar);

// ======================================
// BOTÃO GRAVAÇÃO
// ======================================

const btnRecord = document.getElementById("btnRecord");

if(btnRecord){

    btnRecord.addEventListener("click", toggleGravacao);

    atualizarBotaoGravacao();

}
