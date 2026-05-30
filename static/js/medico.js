// ======================================
// LOGIN MÉDICO (cliente)
// ======================================

const usuario = JSON.parse(
    localStorage.getItem("usuarioLogado")
);

if(!usuario || usuario.tipo !== "Medico"){

    window.location.href = "/login";

}else{

    const nomeEl = document.getElementById("nomeMedico");

    if(nomeEl) nomeEl.innerText = `Dr(a). ${usuario.nome}`;

}

// ======================================
// LOGOUT
// ======================================

function logout(){

    localStorage.removeItem("usuarioLogado");

    // Limpa sessão no servidor
    window.location.href = "/logout";

}

// FUTURO: fetch para carregar pacientes reais

async function carregarRespostas(){

    try{

        const res = await fetch('/api/respostas');

        const data = await res.json();

        const container = document.getElementById('listaPacientes');

        if(!container) return;

        container.innerHTML = '';

        data.forEach(item => {

            const card = document.createElement('div');

            card.className = 'card';

            card.innerHTML = `

                <div class="card-top">

                    <div class="nome">${item.nome}</div>

                    <div class="tipo">${item.tipo}</div>

                </div>

                <div class="info">

                    <div><span class="label">CPF:</span> ${item.cpf}</div>

                    <div style="margin-top:6px;"><span class="label">Pergunta:</span> ${item.pergunta}</div>

                    <div style="margin-top:6px;"><span class="label">Análise IA:</span></div>

                    <div id="resposta-${item.id}" class="resposta-text"></div>

                    <div style="margin-top:8px; font-size:12px; color:#666;">${item.created_at}</div>

                </div>

                <div class="acoes">

                    ${item.audio ? `<a class="btn btn-audio" href="${item.audio}" target="_blank">🔊 Ouvir IA</a>` : ''}

                    <button class="btn btn-visualizar" onclick="editarResposta(${item.id})">✏️ Editar</button>

                    <button class="btn btn-audio" onclick="enviarChroma(${item.id})">💾 Enviar Chroma</button>

                    <button class="btn btn-finalizar" onclick="deletarResposta(${item.id})">🗑 Apagar</button>

                </div>

            `;

            container.appendChild(card);

            const respostaDiv = document.getElementById(`resposta-${item.id}`);

            if(respostaDiv){

                respostaDiv.textContent = item.resposta;

                respostaDiv.dataset.original = item.resposta;

            }

        });

    }catch(e){

        console.error('Erro ao carregar respostas:', e);

    }

}

// ======================================
// EDITAR RESPOSTA
// ======================================

function editarResposta(id){

    const respostaDiv = document.getElementById(`resposta-${id}`);

    if(!respostaDiv) return;

    const textoAtual = respostaDiv.dataset.original || respostaDiv.innerText;

    respostaDiv.innerHTML = `
        <textarea id="resposta-edit-${id}" class="resposta-edit">${textoAtual}</textarea>
        <div class="edit-actions">
            <button class="btn btn-visualizar" onclick="salvarEdicao(${id})">💾 Salvar</button>
            <button class="btn btn-finalizar" onclick="cancelarEdicao(${id})">Cancelar</button>
        </div>
    `;

}

function cancelarEdicao(id){

    const respostaDiv = document.getElementById(`resposta-${id}`);

    if(!respostaDiv) return;

    const original = respostaDiv.dataset.original || '';

    respostaDiv.textContent = original;

}

async function salvarEdicao(id){

    const textarea = document.getElementById(`resposta-edit-${id}`);

    if(!textarea) return;

    const novaResposta = textarea.value.trim();

    if(!novaResposta){

        alert('A resposta não pode ficar vazia.');

        return;

    }

    try{

        const res = await fetch(`/api/respostas/${id}`, {

            method: 'PUT',

            headers: {

                'Content-Type': 'application/json'

            },

            body: JSON.stringify({ resposta: novaResposta })

        });

        if(res.ok){

            const data = await res.json();

            const respostaDiv = document.getElementById(`resposta-${id}`);

            if(respostaDiv){

                respostaDiv.dataset.original = data.resposta || novaResposta;

                respostaDiv.textContent = data.resposta || novaResposta;

            }

            alert('Resposta atualizada com sucesso.');

        }else{

            const errorData = await res.json();

            alert(errorData.erro || 'Erro ao salvar resposta.');

        }

    }catch(e){

        console.error('Erro ao salvar edição:', e);

        alert('Erro ao salvar resposta.');

    }

}

// ======================================
// DELETAR RESPOSTA
// ======================================

async function deletarResposta(id){

    if(!confirm('Tem certeza que deseja apagar esta resposta?')) return;

    try{

        const res = await fetch(`/api/respostas/${id}`, {
            method: 'DELETE'
        });

        if(res.ok){

            alert('Resposta apagada com sucesso!');
            carregarRespostas();

        }else{

            alert('Erro ao apagar resposta');

        }

    }catch(e){

        console.error('Erro ao deletar:', e);
        alert('Erro ao deletar resposta');

    }

}

async function enviarChroma(id){

    try{

        const res = await fetch(`/api/respostas/${id}/chroma`, {
            method: 'POST'
        });

        if(res.ok){
            alert('Dados enviados ao Chroma com sucesso!');
        }else{
            const errorData = await res.json();
            alert(errorData.erro || 'Erro ao enviar ao Chroma');
        }

    }catch(e){
        console.error('Erro ao enviar para o Chroma:', e);
        alert('Erro ao enviar ao Chroma');
    }

}

// carrega ao abrir
carregarRespostas();

// atualiza a cada 20s
setInterval(carregarRespostas, 20000);
