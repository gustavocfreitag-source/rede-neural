// ======================================
// FORMATAR CPF
// ======================================

document
.getElementById("cpf")
.addEventListener("input", function(e){

    let valor = e.target.value.replace(/\D/g,'');

    valor = valor.replace(
        /(\d{3})(\d)/,
        '$1.$2'
    );

    valor = valor.replace(
        /(\d{3})(\d)/,
        '$1.$2'
    );

    valor = valor.replace(
        /(\d{3})(\d{1,2})$/,
        '$1-$2'
    );

    e.target.value = valor;
});

// ======================================
// VALIDAR CPF
// ======================================

function validarCPF(cpf){

    cpf = cpf.replace(/\D/g,'');

    if(cpf.length !== 11){
        return false;
    }

    if(/^(\d)\1+$/.test(cpf)){
        return false;
    }

    let soma = 0;
    let resto;

    for(let i = 1; i <= 9; i++){

        soma += parseInt(
            cpf.substring(i - 1, i)
        ) * (11 - i);
    }

    resto = (soma * 10) % 11;

    if(resto === 10 || resto === 11){
        resto = 0;
    }

    if(resto !== parseInt(cpf.substring(9,10))){
        return false;
    }

    soma = 0;

    for(let i = 1; i <= 10; i++){

        soma += parseInt(
            cpf.substring(i - 1, i)
        ) * (12 - i);
    }

    resto = (soma * 10) % 11;

    if(resto === 10 || resto === 11){
        resto = 0;
    }

    if(resto !== parseInt(cpf.substring(10,11))){
        return false;
    }

    return true;
}

// ======================================
// MOSTRAR MENSAGEM
// ======================================

function mostrarMensagem(texto, tipo = "erro"){

    const div = document.getElementById("mensagem");

    div.className = tipo;

    div.innerText = texto;
}

// ======================================
// LOGIN
// ======================================

async function login(){

    const nome = document
        .getElementById("nome")
        .value
        .trim();

    const cpf = document
        .getElementById("cpf")
        .value;

    const tipo = document
        .getElementById("tipo")
        .value;

    // VALIDA NOME
    if(nome.length < 3){

        mostrarMensagem(
            "Digite um nome válido."
        );

        return;
    }

    // VALIDA CPF
    if(!validarCPF(cpf)){

        mostrarMensagem(
            "CPF inválido."
        );

        return;
    }

    try{

        const resposta = await fetch(
            "/api/login",
            {

                method:"POST",

                headers:{
                    "Content-Type":"application/json"
                },

                body:JSON.stringify({

                    nome:nome,
                    cpf:cpf,
                    tipo:tipo

                })

            }
        );

        const data = await resposta.json();

        if(!resposta.ok){

            mostrarMensagem(
                data.erro || "Erro no login."
            );

            return;
        }

        // SALVA USUÁRIO
        localStorage.setItem(
            "usuarioLogado",
            JSON.stringify(data.usuario)
        );

        mostrarMensagem(
            "Login realizado com sucesso!",
            "sucesso"
        );

        // REDIRECIONA
        setTimeout(() => {

            if(data.usuario && data.usuario.tipo === "Medico"){

                window.location.href = "/medico";

            }else{

                window.location.href = "/triagem";

            }

        }, 1000);

    }catch(erro){

        console.error(erro);

        mostrarMensagem(
            "Erro ao conectar ao servidor."
        );
    }
}

// ======================================
// BOTÃO LOGIN
// ======================================

document
.getElementById("btnLogin")
.addEventListener("click", login);

// ======================================
// ENTER
// ======================================

document.addEventListener(
    "keydown",
    function(e){

        if(e.key === "Enter"){

            login();
        }

    }
);