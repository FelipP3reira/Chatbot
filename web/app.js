// Toda a escrita na tela passa por textContent — nunca por atribuição de HTML
// cru. A resposta do modelo pode carregar o texto de um documento enviado por
// outra pessoa, e uma tag com manipulador de evento viraria código executado no
// navegador de quem lê. Um teste falha se essas APIs aparecerem neste arquivo.

const mensagens = document.getElementById("mensagens");
const formularioDeMensagem = document.getElementById("formulario-mensagem");
const campoDaPergunta = document.getElementById("pergunta");
const botaoDeEnviar = document.getElementById("enviar");

const formularioDeDocumento = document.getElementById("formulario-documento");
const campoDoTitulo = document.getElementById("titulo");
const campoDoConteudo = document.getElementById("conteudo");
const avisoDoDocumento = document.getElementById("aviso-documento");

let conversaId = null;

function acrescentarMensagem(papel, texto) {
  const item = document.createElement("li");
  item.className = `mensagem mensagem--${papel}`;

  const autor = document.createElement("span");
  autor.className = "autor";
  autor.textContent = papel === "usuario" ? "Você" : "Assistente";

  const corpo = document.createElement("p");
  corpo.className = "corpo";
  corpo.textContent = texto;

  item.append(autor, corpo);
  mensagens.append(item);
  item.scrollIntoView({ block: "end" });
  return corpo;
}

async function garantirConversa() {
  if (conversaId) return conversaId;

  const resposta = await fetch("/conversas", { method: "POST" });
  if (!resposta.ok) throw new Error("Não foi possível iniciar a conversa.");

  conversaId = (await resposta.json()).id;
  return conversaId;
}

function lerEvento(bloco) {
  const linhas = bloco.split("\n");
  const nome = linhas[0].replace("event: ", "");
  const dados = JSON.parse(linhas[1].replace("data: ", ""));
  return { nome, dados };
}

async function transmitirResposta(resposta, corpoDaResposta) {
  const leitor = resposta.body.getReader();
  const decodificador = new TextDecoder();
  let pendente = "";

  for (;;) {
    const { done, value } = await leitor.read();
    if (done) break;

    pendente += decodificador.decode(value, { stream: true });

    // O corpo chega em pedaços que não respeitam a fronteira do evento: o
    // último bloco pode estar pela metade e volta para a próxima rodada.
    const blocos = pendente.split("\n\n");
    pendente = blocos.pop();

    for (const bloco of blocos) {
      if (!bloco.trim()) continue;
      const { nome, dados } = lerEvento(bloco);
      if (nome === "pedaco") corpoDaResposta.textContent += dados.texto;
      if (nome === "erro") corpoDaResposta.textContent = dados.mensagem;
    }
  }
}

async function enviarPergunta(pergunta) {
  const id = await garantirConversa();
  const resposta = await fetch(`/conversas/${id}/mensagens`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conteudo: pergunta }),
  });

  const corpoDaResposta = acrescentarMensagem("assistente", "");

  if (!resposta.ok) {
    const erro = await resposta.json();
    corpoDaResposta.textContent = erro.erro.mensagem;
    return;
  }

  await transmitirResposta(resposta, corpoDaResposta);
}

formularioDeMensagem.addEventListener("submit", async (evento) => {
  evento.preventDefault();

  const pergunta = campoDaPergunta.value.trim();
  if (!pergunta) return;

  campoDaPergunta.value = "";
  botaoDeEnviar.disabled = true;
  acrescentarMensagem("usuario", pergunta);

  try {
    await enviarPergunta(pergunta);
  } catch {
    acrescentarMensagem("assistente", "Não consegui falar com o servidor.");
  } finally {
    botaoDeEnviar.disabled = false;
    campoDaPergunta.focus();
  }
});

formularioDeDocumento.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  avisoDoDocumento.textContent = "Processando…";

  const resposta = await fetch("/documentos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      titulo: campoDoTitulo.value,
      conteudo: campoDoConteudo.value,
    }),
  });

  if (!resposta.ok) {
    avisoDoDocumento.textContent = "Não foi possível enviar o documento.";
    return;
  }

  const documento = await resposta.json();
  avisoDoDocumento.textContent = `"${documento.titulo}" indexado em ${documento.trechos} trecho(s).`;
  formularioDeDocumento.reset();
});
